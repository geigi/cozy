from playhouse.sqliteq import SqliteQueueDatabase

from cozy.model.model_base import ModelBase


class DatabaseObject:
    def __init__(self, db: SqliteQueueDatabase, model: ModelBase, table_id: int):
        self.db = db
        self.model = model
        self.id = table_id
        self.__update_db_object()

    def __update_db_object(self):
        with self.db:
            self.db_object = self.model.get_by_id(self.id)

    def get(self, query):
        pass

    def set(self, query):
        pass
