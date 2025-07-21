from ai_designer.freecad.api_client import FreeCADAPIClient

client = FreeCADAPIClient()
client.connect()
client.execute_command('box = Part.makeBox(10, 10, 10)\ndoc.addObject("Part::Feature", "Box").Shape = box')
client.save_document("~/box.FCStd")
client.export_stl(["Box"], "~/box.stl")