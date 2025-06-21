import sys
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/lib/")
sys.path.append("/home/vansh5632/Downloads/squashfs-root/usr/Mod")

import FreeCAD
import FreeCADGui

class FreeCADAPIClient:
    def __init__(self):
        self.connection = None
        self.document = None

    def connect(self):
        """Connect to FreeCAD and create/open a document"""
        try:
            # Initialize FreeCAD if not already done
            if not hasattr(FreeCAD, 'ActiveDocument') or FreeCAD.ActiveDocument is None:
                # Create a new document
                self.document = FreeCAD.newDocument("AutomationDoc")
                print("Connected to FreeCAD and created new document")
            else:
                self.document = FreeCAD.ActiveDocument
                print("Connected to existing FreeCAD document")
            
            self.connection = True
            return True
        except Exception as e:
            print(f"Failed to connect to FreeCAD: {e}")
            return False

    def execute_command(self, command):
        """Execute a FreeCAD command/script"""
        if not self.connection:
            raise ConnectionError("Not connected to FreeCAD")
        
        try:
            # Execute the command in FreeCAD's Python console
            exec(command)
            
            # Recompute the document to update the view
            if self.document:
                self.document.recompute()
            
            return {"status": "success", "message": f"Command executed: {command}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to execute command: {e}"}

    def get_document_objects(self):
        """Get all objects in the current document"""
        if not self.document:
            return []
        
        return [obj.Name for obj in self.document.Objects]

    def get_document_state(self):
        """Get current state of the FreeCAD document"""
        if not self.document:
            return {"objects": [], "active_document": None}
        
        objects_info = []
        for obj in self.document.Objects:
            obj_info = {
                "name": obj.Name,
                "type": obj.TypeId,
                "label": obj.Label
            }
            objects_info.append(obj_info)
        
        return {
            "active_document": self.document.Name,
            "objects": objects_info,
            "object_count": len(self.document.Objects)
        }