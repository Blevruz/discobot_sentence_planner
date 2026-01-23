# chatbot/middle_modules/neo4j_request.py
from middle_modules.dummy import DummyMiddle
from neo4j import GraphDatabase

# Utility class to manage neo4j databases
class Neo4jManager:

    def __init__(self, neo4j_uri = "bolt://127.0.0.1:7687", neo4j_auth = ("neo4j", "neo4j")):
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
        self._check_fulltext_index()

    def _check_fulltext_index(self):
        index_name = "test_index"
        labels = ["test_node"]
        props = "name"
        query = f"""
            CREATE FULLTEXT INDEX `{index_name}` IF NOT EXISTS
            FOR (n:{'|'.join(labels)}) ON EACH {props}
        """
        return self.driver.execute_query(query)

    def execute_query(self, query, params={}):
        if not self.neo4j_available:
            logging.warning("Neo4j not available.  Returning empty result.")
            return []
        try:
            print(f"EXECUTING: {query}")
            with self.driver.session() as session:
                result = session.run(query, **params)
                print(f"EXECUTED: {result.data()}")
                return result.data()
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            return []

    def _add_params(self, params={}):
        # A way to handle arbitrary params
        conditions = []
        keys = list(params.keys())
        values = list(params.values())
        for key, value in zip(keys, values):
            if key[0] != "_":
                params[f"_{key}"] = key
                conditions.append(f"{key}: ${key}")
        return f"{{{', '.join(conditions)}}}"

    def set_node(self, node_type, params={}):
        query = f"MERGE (d: $($node_type) {self._add_params(params)}) RETURN d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def get_node(self, node_type, params={}):
        query = f"MATCH (d: $($node_type) {self._add_params(params)}) RETURN d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def del_node(self, node_type, params={}):
        query = f"MATCH (d: $($node_type) {self._add_params(params)}) DETACH DELETE d\n"
        params["node_type"] = node_type
        return self.execute_query(query, params)

    def set_relation(self, node1_type, node2_type, relation,
                     node1_params={}, node2_params={}):
        query = f"MATCH (d1: $($node1_type) {self._add_params(node1_params)}), "
        query += f"(d2: $($node2_type) {self._add_params(node2_params)}) "
        query += "CREATE (d1)-[r:$($relation)]->(d2) RETURN r\n"
        params = {"node1_type": node1_type,
                  "node2_type": node2_type,
                  "relation": relation,
                  **node1_params, **node2_params}
        return self.execute_query(query, params)

    def get_relation(self, node1_type, node2_type, relation,
                     node1_params={}, node2_params={}):
        query = f"MATCH (d1: $($node1_type) {self._add_params(node1_params)}), "
        query += f"(d2: $($node2_type) {self._add_params(node2_params)}) "
        query += "MATCH (d1)-[r:$($relation)]->"+"(d2) RETURN r\n"
        params = {"node1_type": node1_type,
                  "node2_type": node2_type,
                  "relation": relation,
                  **node1_params, **node2_params}
        return self.execute_query(query, params)

class Neo4jRequest(DummyMiddle):
    """Sends received input to a Neo4j database and returns the response in a
    queue.
    Multiple input queues for multiple purposes:
    - triplets: a list of strings in a subject-relation-object format
    to be added to the database
    - query: a string to be searched for in the database
    """

    def action(self, i):
        if not self.input_queue.empty():

    def __init__(self, name="neo4j_request", **args):
        """Initializes the module.
        Arguments:
            neo4j_uri : str
                URI of the Neo4j database
            neo4j_auth : tuple
                Authentication credentials for the Neo4j database
        """
        DummyMiddle.__init__(self, name, **args)
        self._neo4j_uri = args.get('neo4j_uri', "bolt://127.0.0.1:7687")
        self._neo4j_auth = args.get('neo4j_auth', ("neo4j", "neo4j"))
        self.neo4j_manager = Neo4jManager(self._neo4j_uri, self._neo4j_auth)

        # Expecting ["subject", "predicate", "object"] triplets as input
        self._input_queues['triplets'] = QueueSlot(self, \
                'input', datatype='triplet')
        # Expecting strings as input
        self._input_queues['query'] = QueueSlot(self, \
                'input', datatype='string')

