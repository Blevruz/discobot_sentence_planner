# chatbot/middle_modules/neo4j_request.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from neo4j import GraphDatabase
from utils.queues import QueueSlot
import utils.config
import logging

# Utility class to manage neo4j databases
class Neo4jManager:

    def __init__(self, neo4j_uri="bolt://127.0.0.1:7687", neo4j_auth=("neo4j", "neo4j")):
        self.neo4j_available = False
        self.driver = None
        self.local_storage = {}  # Fallback local

        self.init_neo4j(neo4j_uri, neo4j_auth)

    def init_neo4j(self, neo4j_uri, neo4j_auth):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        try:
            self.driver.verify_connectivity()
            self.neo4j_available = True
        except Exception as e:
            print(f"Exception raised connecting to Neo4j: {e}")
        # Ensure database has a fulltext index
        if self.neo4j_available:
            self._setup_fulltext_index()

    def _drop_index(self, index_name="test_index"):
        query = f"""
            DROP INDEX {index_name} IF EXISTS
        """

    def _setup_fulltext_index(self, index_name="test_index",
                               labels=["test_node"],
                               props="[n.name]"):
        query = """
            CREATE FULLTEXT INDEX $index_name IF NOT EXISTS
            FOR (n:test_node)
            ON EACH [n.name]
            OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard' } }
        """
        self.driver.execute_query(query, {"index_name": index_name})

    #def _setup_embedding_index(self, index_name="test_index", 
    #                           labels=["test_node"],
    #                           props="[n.name]"):


    def execute_query(self, query, params=None):
        if params is None:
            params = {}
        if not self.neo4j_available:
            logging.warning("Neo4j not available. Returning empty result.")
            return []
        try:
            with self.driver.session() as session:
                result = session.run(query, **params)
                return result.data()
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            return []

    # ---------------- FULLTEXT SEARCH ---------------- #
    def fulltext_search(self, search_string, index_name="test_index", limit=10):
        """Run a Neo4j fulltext query and return matching nodes."""
        query = """
        CALL db.index.fulltext.queryNodes($index_name, $search_string)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """
        params = {
            "index_name": index_name,
            "search_string": f"{search_string}~",
            "limit": limit,
        }
        return self.execute_query(query, params)


class Neo4jRequest(DummyMiddle):
    """Handles triplet insertions and fulltext search queries."""

    def __init__(self, name="neo4j_request", **args):
        DummyMiddle.__init__(self, name, **args)
        self._neo4j_uri = args.get('neo4j_uri', "bolt://127.0.0.1:7687")
        self._neo4j_auth = args.get('neo4j_auth', ("neo4j", "neo4j"))
        self._neo4j_auth = (self._neo4j_auth[0], self._neo4j_auth[1])
        self.neo4j_manager = Neo4jManager(self._neo4j_uri, self._neo4j_auth)
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
                results = self.neo4j_manager.fulltext_search(search_string)

                # Push results to output queue
                if 'output' in self._output_queues:
                    self._output_queues['output'][0].put(results)

middle_modules_class['neo4j_request'] = Neo4jRequest
