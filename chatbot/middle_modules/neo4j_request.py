# chatbot/middle_modules/neo4j_request.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.neo4j_utils import Neo4jManager
from neo4j import GraphDatabase
from utils.queues import QueueSlot
import utils.config
import logging


class Neo4jRequest(DummyMiddle):
    """Handles triplet insertions and fulltext search queries."""

    def __init__(self, name="neo4j_request", **args):
        DummyMiddle.__init__(self, name, **args)
        self._neo4j_uri = args.get('neo4j_uri', "bolt://127.0.0.1:7687")
        self._neo4j_auth = args.get('neo4j_auth', ("neo4j", "neo4j"))
        self._neo4j_auth = (self._neo4j_auth[0], self._neo4j_auth[1])
        self.neo4j_manager = Neo4jManager(self._neo4j_uri, self._neo4j_auth)
        self._index_name = args.get('index_name', "test_index")
        self._labels = args.get('labels', ["test_node"])
        self._props = args.get('props', ["name"])
        self.neo4j_manager._check_fulltext_index(self._index_name, self._labels, self._props)
        self._loop_type = 'process'

        del self._input_queues['input']
        # Expecting ["subject", "predicate", "object"] triplets as input
        self._input_queues['triplets'] = QueueSlot(self, 'input', datatype='triplet')
        # Expecting strings as input for fulltext search
        self._input_queues['query'] = QueueSlot(self, 'input', datatype='string')

        self._input_queues['default'] = self._input_queues['triplets']

    def action(self, i):
        if len(self._input_queues['triplets']) > 0:
            # --- Handle triplets ---
            triplet = self._input_queues['triplets'][0].get()
            if triplet is not None:
                if len(triplet) == 3: 
                    subject, predicate, obj = triplet

                    query = """
                    MERGE (s:test_node {name:$subject})
                    MERGE (o:test_node {name:$object})
                    MERGE (s)-[:REL {type:$predicate}]->(o)
                    RETURN s, o
                    """
                    if utils.config.verbose:
                        utils.config.debug_print(f"[{self.name}]Sending query {query} with params {subject}, {obj}, {predicate}")
                    self.neo4j_manager.execute_query(query, {
                        "subject": subject,
                        "object": obj,
                        "predicate": predicate,
                    })

        if len(self._input_queues['query']) > 0:
            # --- Handle fulltext search queries ---
            search_string = self._input_queues['query'][0].get()
            if search_string is not None:
                results = self.fulltext_search(search_string)

                # Push results to output queue
                if 'output' in self._output_queues:
                    self._output_queues['output'][0].put(results)

    
    def fulltext_search(self, search_string, limit=10):
        """Run a Neo4j fulltext query and return matching nodes."""
        query = """
        CALL db.index.fulltext.queryNodes($index_name, $search_string)
        YIELD node, score
        MATCH (node)-[r]->(related)
        RETURN node, score, type(r) AS relation_type,
            labels(node) AS node_labels, elementId(node) AS node_id,
            node.name AS node_name, elementId(related) AS related_id, 
            labels(related) AS related_labels, related.name AS related_name
        ORDER BY score DESC
        LIMIT $limit
        """
        params = {
            "index_name": self._index_name,
            "search_string": f"{search_string}~",
            "limit": limit,
        }
        return self.neo4j_manager.execute_query(query, params)

middle_modules_class['neo4j_request'] = Neo4jRequest
