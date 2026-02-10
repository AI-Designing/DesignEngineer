"""
Orchestrator Agent - Coordinates multi-agent design workflow.

This agent manages the complete design pipeline:
1. Planner: Decomposes design into task graph
2. Generator: Creates FreeCAD scripts from tasks
3. Validator: Assesses quality and suggests refinements
4. Refiner: Iterates until validation passes or max iterations reached
"""

import structlog
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.core.exceptions import AIDesignerError
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.core.logging_config import get_logger
from ai_designer.schemas.design_state import (
    AgentType,
    DesignRequest,
    DesignState,
    ExecutionStatus,
    IterationState,
)
from ai_designer.schemas.task_graph import TaskGraph
from ai_designer.schemas.validation import ValidationResult

logger = get_logger(__name__)


class OrchestratorAgent:
    """
    Orchestrates the multi-agent design workflow.
    
    Coordinates Planner → Generator → Validator in an iterative loop,
    handling refinement cycles until a valid design is produced or
    maximum iterations are exceeded.
    """

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        planner: Optional[PlannerAgent] = None,
        generator: Optional[GeneratorAgent] = None,
        validator: Optional[ValidatorAgent] = None,
        max_iterations: int = 5,
        enable_refinement: bool = True,
    ):
        """
        Initialize the Orchestrator Agent.

        Args:
            llm_provider: Unified LLM provider for all agents
            planner: Optional pre-configured Planner agent
            generator: Optional pre-configured Generator agent
            validator: Optional pre-configured Validator agent
            max_iterations: Maximum refinement iterations (1-10)
            enable_refinement: Whether to enable refinement loops

        Raises:
            ValueError: If max_iterations is out of valid range
        """
        if not 1 <= max_iterations <= 10:
            raise ValueError("max_iterations must be between 1 and 10")

        self.llm_provider = llm_provider
        self.max_iterations = max_iterations
        self.enable_refinement = enable_refinement

        # Initialize agents (use provided or create new)
        self.planner = planner or PlannerAgent(llm_provider=llm_provider)
        self.generator = generator or GeneratorAgent(llm_provider=llm_provider)
        self.validator = validator or ValidatorAgent(llm_provider=llm_provider)

        logger.info(
            "Initialized OrchestratorAgent",
            max_iterations=max_iterations,
            enable_refinement=enable_refinement,
        )

    async def execute(
        self,
        request: DesignRequest,
        execution_callback: Optional[Any] = None,
    ) -> DesignState:
        """
        Execute the complete design workflow.

        Args:
            request: User's design request
            execution_callback: Optional callback for FreeCAD script execution

        Returns:
            DesignState: Final design state with results or errors

        The workflow:
        1. Plan: Decompose design into task graph
        2. Generate: Create FreeCAD scripts
        3. Execute: Run scripts (if callback provided)
        4. Validate: Assess quality
        5. Refine: Loop if needed and enabled
        """
        # Initialize design state
        state = DesignState(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
            max_iterations=self.max_iterations,
        )

        logger.info(
            "Starting design workflow",
            request_id=str(request.request_id),
            prompt=request.user_prompt[:100],
        )

        # Track workflow iterations separately
        workflow_iteration = 0
        
        try:
            # Main workflow loop
            while workflow_iteration < self.max_iterations:
                workflow_iteration += 1
                
                logger.info(
                    "Starting iteration",
                    iteration=workflow_iteration,
                    max_iterations=self.max_iterations,
                )

                # Step 1: Planning (first iteration or replanning)
                if workflow_iteration == 1:
                    task_graph = await self._plan(state, request)
                else:
                    # Replan based on validation feedback
                    task_graph = await self._replan(state, request)

                if task_graph is None:
                    state.mark_failed("Planning failed - no task graph generated")
                    break

                # Step 2: Generation
                scripts = await self._generate(state, request, task_graph)
                
                if not scripts:
                    state.mark_failed("Generation failed - no scripts produced")
                    break

                # Step 3: Execution (optional)
                execution_result = None
                if execution_callback:
                    execution_result = await self._execute_scripts(
                        scripts, execution_callback
                    )

                # Step 4: Validation
                validation = await self._validate(
                    state, request, task_graph, scripts, execution_result
                )

                # Update current iteration to match workflow iteration
                state.current_iteration = workflow_iteration
                
                # Check validation outcome
                if validation.is_valid:
                    # Success!
                    state.is_valid = True
                    state.mark_completed()
                    logger.info(
                        "Design validated successfully",
                        iteration=workflow_iteration,
                        score=validation.overall_score,
                    )
                    break

                elif validation.should_refine and self.enable_refinement:
                    # Can refine - continue loop
                    logger.info(
                        "Design needs refinement",
                        iteration=workflow_iteration,
                        score=validation.overall_score,
                        suggestions=len(validation.refinement_suggestions),
                    )
                    state.status = ExecutionStatus.REFINING
                    # Loop will continue to replan
                else:
                    # Cannot improve - fail
                    state.mark_failed(
                        f"Design validation failed (score: {validation.overall_score:.2f})",
                        details={
                            "validation": validation.model_dump(),
                            "iteration": workflow_iteration,
                        },
                    )
                    break

            # Check if we exceeded max iterations
            if (
                state.status == ExecutionStatus.REFINING
                and workflow_iteration >= self.max_iterations
            ):
                state.mark_failed(
                    f"Maximum iterations ({self.max_iterations}) exceeded without valid design"
                )

        except Exception as e:
            logger.error("Workflow execution failed", error=str(e), exc_info=True)
            state.mark_failed(
                f"Unexpected error: {str(e)}",
                details={"exception_type": type(e).__name__},
            )

        # Ensure current_iteration reflects final count
        if workflow_iteration > 0:
            state.current_iteration = workflow_iteration
            
        logger.info(
            "Design workflow completed",
            request_id=str(request.request_id),
            status=state.status.value,
            iterations=len(state.iterations),
        )

        return state

    async def _plan(
        self, state: DesignState, request: DesignRequest
    ) -> Optional[TaskGraph]:
        """Execute planning phase."""
        state.status = ExecutionStatus.PLANNING
        # Track agent step (iterations list) without incrementing current_iteration
        iteration = IterationState(
            iteration_number=len(state.iterations) + 1,
            agent=AgentType.PLANNER,
        )
        state.iterations.append(iteration)
        state.updated_at = datetime.utcnow()

        try:
            logger.info("Executing planning phase")
            task_graph = await self.planner.plan(request)

            # Store results
            state.task_graph_id = str(task_graph.request_id)
            state.execution_plan = {
                "task_count": len(task_graph.nodes),
                "dependencies": len(task_graph.edges),
                "execution_order": task_graph.get_execution_order(),
            }

            iteration.output = {
                "task_graph_id": str(task_graph.request_id),
                "task_count": len(task_graph.nodes),
            }
            iteration.completed_at = state.updated_at

            logger.info(
                "Planning completed",
                task_count=len(task_graph.nodes),
                dependencies=len(task_graph.edges),
            )

            return task_graph

        except Exception as e:
            logger.error("Planning failed", error=str(e))
            iteration.errors.append(f"Planning error: {str(e)}")
            iteration.completed_at = state.updated_at
            return None

    async def _replan(
        self, state: DesignState, request: DesignRequest
    ) -> Optional[TaskGraph]:
        """Execute replanning phase based on validation feedback."""
        state.status = ExecutionStatus.PLANNING
        # Track agent step (iterations list) without incrementing current_iteration
        iteration = IterationState(
            iteration_number=len(state.iterations) + 1,
            agent=AgentType.PLANNER,
        )
        state.iterations.append(iteration)
        state.updated_at = datetime.utcnow()

        try:
            # Get previous validation feedback
            previous_validation = state.validation_results
            feedback = []
            
            if previous_validation:
                if "refinement_suggestions" in previous_validation:
                    feedback = previous_validation["refinement_suggestions"]

            logger.info("Executing replanning phase", feedback_count=len(feedback))

            # Use planner's replan method with feedback
            task_graph = await self.planner.replan(request, feedback)

            # Store results
            state.task_graph_id = str(task_graph.request_id)
            state.execution_plan = {
                "task_count": len(task_graph.nodes),
                "dependencies": len(task_graph.edges),
                "execution_order": task_graph.get_execution_order(),
                "replanned": True,
            }

            iteration.output = {
                "task_graph_id": str(task_graph.request_id),
                "task_count": len(task_graph.nodes),
                "replanned": True,
            }
            iteration.completed_at = state.updated_at

            logger.info("Replanning completed", task_count=len(task_graph.nodes))

            return task_graph

        except Exception as e:
            logger.error("Replanning failed", error=str(e))
            iteration.errors.append(f"Replanning error: {str(e)}")
            iteration.completed_at = state.updated_at
            return None

    async def _generate(
        self, state: DesignState, request: DesignRequest, task_graph: TaskGraph
    ) -> Optional[Dict[str, str]]:
        """Execute generation phase."""
        state.status = ExecutionStatus.GENERATING
        # Track agent step (iterations list) without incrementing current_iteration
        iteration = IterationState(
            iteration_number=len(state.iterations) + 1,
            agent=AgentType.GENERATOR,
        )
        state.iterations.append(iteration)
        state.updated_at = datetime.utcnow()

        try:
            logger.info("Executing generation phase")
            scripts = await self.generator.generate(request, task_graph)

            # Store results
            state.freecad_script = "\n\n".join(scripts.values())
            state.script_artifacts = {
                "task_scripts": list(scripts.keys()),
                "script_count": len(scripts),
                "total_lines": sum(len(s.split("\n")) for s in scripts.values()),
            }

            iteration.output = {
                "script_count": len(scripts),
                "tasks": list(scripts.keys()),
            }
            iteration.completed_at = state.updated_at

            logger.info("Generation completed", script_count=len(scripts))

            return scripts

        except Exception as e:
            logger.error("Generation failed", error=str(e))
            iteration.errors.append(f"Generation error: {str(e)}")
            iteration.completed_at = state.updated_at
            return None

    async def _execute_scripts(
        self, scripts: Dict[str, str], callback: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Execute FreeCAD scripts using provided callback.
        
        Args:
            scripts: Generated FreeCAD scripts
            callback: Execution callback function
            
        Returns:
            Execution results or None if execution fails
        """
        try:
            logger.info("Executing FreeCAD scripts", script_count=len(scripts))
            
            # Call the execution callback
            result = await callback(scripts)
            
            logger.info("Script execution completed")
            return result
            
        except Exception as e:
            logger.error("Script execution failed", error=str(e))
            return {"error": str(e), "success": False}

    async def _validate(
        self,
        state: DesignState,
        request: DesignRequest,
        task_graph: TaskGraph,
        scripts: Dict[str, str],
        execution_result: Optional[Dict[str, Any]],
    ) -> ValidationResult:
        """Execute validation phase."""
        state.status = ExecutionStatus.VALIDATING
        # Track agent step (iterations list) without incrementing current_iteration
        iteration = IterationState(
            iteration_number=len(state.iterations) + 1,
            agent=AgentType.VALIDATOR,
        )
        state.iterations.append(iteration)
        state.updated_at = datetime.utcnow()

        try:
            logger.info("Executing validation phase")
            validation = await self.validator.validate(
                request, task_graph, scripts, execution_result
            )

            # Store results
            state.validation_results = validation.model_dump()
            state.is_valid = validation.is_valid

            iteration.output = {
                "is_valid": validation.is_valid,
                "overall_score": validation.overall_score,
                "geometric_score": validation.geometric_score,
                "semantic_score": validation.semantic_score,
                "should_refine": validation.should_refine,
            }
            iteration.completed_at = state.updated_at

            logger.info(
                "Validation completed",
                is_valid=validation.is_valid,
                score=validation.overall_score,
            )

            return validation

        except Exception as e:
            logger.error("Validation failed", error=str(e))
            iteration.errors.append(f"Validation error: {str(e)}")
            iteration.completed_at = state.updated_at
            
            # Return a failed validation
            from ai_designer.schemas.validation import ValidationResult
            return ValidationResult(
                request_id=str(request.request_id),
                is_valid=False,
            )
