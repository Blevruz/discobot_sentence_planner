# chatbot/middle_modules/neo4j_request.py
from middle_modules.dummy import DummyMiddle
from neo4j import GraphDatabase

class Neo4jRequest(DummyMiddle):

    def action(self, i):
        if not self.input_queue.empty():

