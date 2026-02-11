"""
LangGraph node wrappers for all agents.

Each node function receives PipelineState and returns updated PipelineState.
Nodes are responsible for:
- Calling the appropriate agent
- Updating state with results
- Handling errors gracefully
- Recording timing metrics
"""

from datetime import datetime
from typing import Any, Callable, Optional

import structlog

from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.core.exceptions import AIDesignerError
from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.orchestration.state import PipelineState
from ai_designer.schemas.design_state import (
    AgentType,
    DesignRequest,
    ExecutionStatus,
    IterationState,
)

logger = structlog.get_logger(__name__)


class PipelineNodes:
    """
    Collection of LangGraph node functions for the design pipeline.
    
    Each method is a node in the state graph that processes PipelineState
    and returns updated PipelineState.
    """
    
    def __init__(
        self,
        planner: PlannerAgent,
        generator: GeneratorAgent,
        validator: ValidatorAgent,
        executor: Optional[FreeCADExecutor] = None,
        websocket_callback: Optional[Callable] = None,
    ):
        """
        Initialize pipeline nodes with agents.
        
        Args:
            planner: Planner agent instance
            generator: Generator agent instance
            validator: Validator agent instance
            executor: Optional FreeCAD executor
            websocket_callback: Optional callback for WebSocket updates
        """
        self.planner = planner
        self.generator = generator
        self.validator = validator
        self.executor = executor
        self.websocket_callback = websocket_callback
    
    async def planner_node(self, state: PipelineState) -> PipelineState:
        """
        Planning node: Decompose design into task graph.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with task graph
        """
        state.enter_node("planner")
        state.design_state.status = ExecutionStatus.PLANNING
        
        # Record iteration in design state
        iteration = IterationState(
            iteration_number=len(state.design_state.iterations) + 1,
            agent=AgentType.PLANNER,
        )
        state.design_state.iterations.append(iteration)
        state.design_state.updated_at = datetime.utcnow()
        
        try:
            logger.info(
                "Executing planner node",
                iteration=state.workflow_iteration,
                request_id=str(state.design_state.request_id),
            )
            
            # Create design request from state
            request = DesignRequest(
                request_id=state.design_state.request_id,
                user_prompt=state.design_state.user_prompt,
            )
            
            # Call planner agent
            task_graph = await self.planner.plan(request)
            
            # Update state
            state.task_graph = task_graph
            state.design_state.task_graph_id = str(task_graph.request_id)
            state.design_state.execution_plan = {
                "task_count": len(task_graph.nodes),
                "dependencies": len(task_graph.edges),
                "complexity": task_graph.complexity_score,
            }
            
            iteration.output_summary = f"Generated {len(task_graph.nodes)} tasks"
            iteration.completed_at = datetime.utcnow()
            
            # WebSocket callback
            if self.websocket_callback:
                await self.websocket_callback(
                    state.design_state.request_id,
                    {
                        "node": "planner",
                        "status": "completed",
                        "task_count": len(task_graph.nodes),
                    },
                )
            
            logger.info(
                "Planner node completed",
                task_count=len(task_graph.nodes),
                complexity=task_graph.complexity_score,
            )
            
        except Exception as e:
            logger.error("Planner node failed", error=str(e), exc_info=True)
            state.record_error(f"Planning failed: {str(e)}", "planner")
            iteration.error_message = str(e)
            state.design_state.mark_failed(f"Planning failed: {str(e)}")
        
        finally:
            state.exit_node()
        
        return state
    
    async def generator_node(self, state: PipelineState) -> PipelineState:
        """
        Generator node: Create FreeCAD scripts from task graph.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with generated scripts
        """
        state.enter_node("generator")
        state.design_state.status = ExecutionStatus.GENERATING
        
        # Record iteration in design state
        iteration = IterationState(
            iteration_number=len(state.design_state.iterations) + 1,
            agent=AgentType.GENERATOR,
        )
        state.design_state.iterations.append(iteration)
        state.design_state.updated_at = datetime.utcnow()
        
        try:
            logger.info(
                "Executing generator node",
                iteration=state.workflow_iteration,
                task_count=len(state.task_graph.nodes) if state.task_graph else 0,
            )
            
            if not state.task_graph:
                raise AIDesignerError("No task graph available for generation")
            
            # Create design request
            request = DesignRequest(
                request_id=state.design_state.request_id,
                user_prompt=state.design_state.user_prompt,
            )
            
            # Include validation feedback if refining
            feedback = None
            if state.validation_result and state.workflow_iteration > 1:
                feedback = state.validation_result.refinement_suggestions
            
            # Call generator agent
            scripts = await self.generator.generate(
                request=request,
                task_graph=state.task_graph,
                refinement_feedback=feedback,
            )
            
            # Update state
            state.generated_scripts = scripts
            state.design_state.freecad_script = scripts.get("main", "")
            state.design_state.generated_code = scripts
            
            iteration.output_summary = f"Generated {len(scripts)} scripts"
            iteration.completed_at = datetime.utcnow()
            
            # WebSocket callback
            if self.websocket_callback:
                await self.websocket_callback(
                    state.design_state.request_id,
                    {
                        "node": "generator",
                        "status": "completed",
                        "script_count": len(scripts),
                    },
                )
            
            logger.info(
                "Generator node completed",
                script_count=len(scripts),
                has_feedback=feedback is not None,
            )
            
        except Exception as e:
            logger.error("Generator node failed", error=str(e), exc_info=True)
            state.record_error(f"Generation failed: {str(e)}", "generator")
            iteration.error_message = str(e)
            state.design_state.mark_failed(f"Generation failed: {str(e)}")
        
        finally:
            state.exit_node()
        
        return state
    
    async def executor_node(self, state: PipelineState) -> PipelineState:
        """
        Executor node: Run FreeCAD scripts in sandbox.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with execution results
        """
        state.enter_node("executor")
        state.design_state.status = ExecutionStatus.EXECUTING
        
        try:
            logger.info(
                "Executing executor node",
                iteration=state.workflow_iteration,
                has_executor=self.executor is not None,
            )
            
            if not self.executor:
                logger.info("No executor configured, skipping execution")
                state.execution_result = {"skipped": True, "reason": "No executor configured"}
                return state
            
            if not state.generated_scripts:
                raise AIDesignerError("No generated scripts available for execution")
            
            # Execute main script
            main_script = state.generated_scripts.get("main")
            if not main_script:
                raise AIDesignerError("No main script found in generated scripts")
            
            result = await self.executor.execute(main_script)
            
            # Update state
            state.execution_result = {
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error"),
                "execution_time": result.get("execution_time", 0),
            }
            state.design_state.execution_result = result
            
            # WebSocket callback
            if self.websocket_callback:
                await self.websocket_callback(
                    state.design_state.request_id,
                    {
                        "node": "executor",
                        "status": "completed",
                        "success": result.get("success", False),
                    },
                )
            
            logger.info(
                "Executor node completed",
                success=result.get("success", False),
                execution_time=result.get("execution_time", 0),
            )
            
        except Exception as e:
            logger.error("Executor node failed", error=str(e), exc_info=True)
            state.record_error(f"Execution failed: {str(e)}", "executor")
            state.execution_result = {
                "success": False,
                "error": str(e),
            }
        
        finally:
            state.exit_node()
        
        return state
    
    async def validator_node(self, state: PipelineState) -> PipelineState:
        """
        Validator node: Assess design quality and provide feedback.
        
        Args:
            state: Current pipeline state
            
        Returns:
            Updated pipeline state with validation result
        """
        state.enter_node("validator")
        state.design_state.status = ExecutionStatus.VALIDATING
        
        # Record iteration in design state
        iteration = IterationState(
            iteration_number=len(state.design_state.iterations) + 1,
            agent=AgentType.VALIDATOR,
        )
        state.design_state.iterations.append(iteration)
        state.design_state.updated_at = datetime.utcnow()
        
        try:
            logger.info(
                "Executing validator node",
                iteration=state.workflow_iteration,
            )
            
            if not state.task_graph:
                raise AIDesignerError("No task graph available for validation")
            
            if not state.generated_scripts:
                raise AIDesignerError("No generated scripts available for validation")
            
            # Create design request
            request = DesignRequest(
                request_id=state.design_state.request_id,
                user_prompt=state.design_state.user_prompt,
            )
            
            # Call validator agent
            validation = await self.validator.validate(
                request=request,
                task_graph=state.task_graph,
                generated_scripts=state.generated_scripts,
                execution_result=state.execution_result,
            )
            
            # Update state
            state.validation_result = validation
            state.design_state.validation_result = validation
            state.design_state.is_valid = validation.is_valid
            
            iteration.output_summary = f"Score: {validation.overall_score:.2f}"
            iteration.completed_at = datetime.utcnow()
            
            # WebSocket callback
            if self.websocket_callback:
                await self.websocket_callback(
                    state.design_state.request_id,
                    {
                        "node": "validator",
                        "status": "completed",
                        "score": validation.overall_score,
                        "is_valid": validation.is_valid,
                    },
                )
            
            logger.info(
                "Validator node completed",
                score=validation.overall_score,
                is_valid=validation.is_valid,
                should_refine=validation.should_refine,
            )
            
        except Exception as e:
            logger.error("Validator node failed", error=str(e), exc_info=True)
            state.record_error(f"Validation failed: {str(e)}", "validator")
            iteration.error_message = str(e)
            state.design_state.mark_failed(f"Validation failed: {str(e)}")
        
        finally:
            state.exit_node()
        
        return state
