# import threading
# from queue import Queue
# import time
#
# print_lock = threading.Lock()
#
#
# def exampleJob(worker):
#     time.sleep(0.5)
#
#     with print_lock:
#         print(threading.current_thread().name, worker)
#
# def threader():
#     while True:
#         worker = q.get()
#         exampleJob(worker)
#         q.task_done()
#
#
# q = Queue()
#
#
#
# for x in range(10):
#     t = threading.Thread(target = threader)
#     t.daemon = True
#     t.start()
#
# start = time.time()

from listeners.tick import GameThread
from queue import Queue
from time import time as timestamp, sleep
import pymysql.cursors


class ThreadedMySQL:

    def __init__(self):
        self.thread_status = False

        # Regular Queue
        self._r_queue = Queue()
        # Prioitized Queue
        self._p_queue = Queue()

        self.connection_method = 0

        self._debug = True

        self.wait = 0


    def wait(self, delay):
        self.wait = delay


    def execute(self, query, args=None, callback=None, data_pack=None, prioritize=False, get_info=False):
        """
            This function cannot pass fetch data to the callback!

        :param query: The SQL query that you want to execute
        :param args: If the query have any args
        :param callback: The callback for the query
        :param data_pack: If you want to pass more to the callback than the query
        :param prioritize: If you have large queues prioritizing the query can make it finish
         before the rest of the queue is finished
        :param get_info: If you want information passed to the callback
         (such as timestamp, query and prioritized)
        :return:
        """
        query_type = 0

        # If callback = None assuming no data returned needed
        if get_info:
            get_info = {'query': query, 'time': timestamp(), 'prioritized': prioritize}

        if not prioritize:
            self._r_queue.put([query, args, callback, data_pack, get_info, query_type])
        else:
            self._p_queue.put([query, args, callback, data_pack, get_info, query_type])

    def fetchone(self, query, args=None, callback=None, data_pack=None, prioritize=False, get_info=False):
        """
            This function both execute and fetch data, no need to execute before using this!

        :param query: The SQL query that you want to execute
        :param args: If the query have any args
        :param callback: The callback for the query
        :param data_pack: If you want to pass more to the callback than the query
        :param prioritize: If you have large queues prioritizing the query can make it finish
         before the rest of the queue is finished
        :param get_info: If you want information passed to the callback
         (such as timestamp, query and prioritized)
        :return:
        """
        query_type = 1
        if get_info:
            get_info = {'query': query, 'time': timestamp(), 'prioritized': prioritize}

         # If callback = None assuming no data returned needed
        if not prioritize:
            self._r_queue.put([query, args, callback, data_pack, get_info, query_type])
        else:
            self._p_queue.put([query, args, callback, data_pack, get_info, query_type])


    def fetchall(self, query, args=None, callback=None, data_pack=None, prioritize=False, get_info=False):
        """
          This function both execute and fetch data, no need to execute before using this!

        :param query: The SQL query that you want to execute
        :param args: If the query have any args
        :param callback: The callback for the query
        :param data_pack: If you want to pass more to the callback than the query
        :param prioritize: If you have large queues prioritizing the query can make it finish
         before the rest of the queue is finished
        :param get_info: If you want information passed to the callback
         (such as timestamp, query and prioritized)
        :return:
        """
        query_type = 2

        if get_info:
            get_info = {'query': query, 'time': timestamp(), 'prioritized': prioritize}

        # If callback = None assuming no data returned needed
        if not prioritize:
            self._r_queue.put([query, args, callback, data_pack, get_info, query_type])
        else:
            self._p_queue.put([query, args, callback, data_pack, get_info, query_type])

    def complete_task(self, worker, prio=None):
        query = worker[0]
        args = worker[1]
        callback = worker[2]
        data_pack = worker[3]
        get_info = worker[4]
        query_type = worker[5]
        try:
            if get_info:
                get_info['time'] = timestamp() - get_info['time']

            if args:
                self.cursor.execute(query, args)
            else:
                self.cursor.execute(query)

            if query_type == 0:
                if get_info:
                    if callback:
                        if data_pack:
                            callback(data_pack, get_info)
                        else:
                            callback(get_info)
                else:
                    if callback:
                        if data_pack:
                            callback(data_pack)
                        else:
                            callback()
            if query_type == 1:
                data = self.cursor.fetchone()
                if get_info:
                    if callback:
                        if data_pack:
                            callback(data, data_pack, get_info)
                        else:
                            callback(data, get_info)
                else:
                    if callback:
                        if data_pack:
                            callback(data, data_pack)
                        else:
                            callback(data)

            if query_type == 2:
                data = self.cursor.fetchall()
                if get_info:
                    if callback:
                        if data_pack:
                            callback(data, data_pack, get_info)
                        else:
                            callback(data, get_info)
                else:
                    if callback:
                        if data_pack:
                            callback(data, data_pack)
                        else:
                            callback(data)
            if prio:
                self._p_queue.task_done()
            else:
                self._r_queue.task_done()

        except:
            pass

    def _threader(self):
        while self.thread_status:
            if self.wait:
                sleep(self.wait)

            if self._p_queue.empty():
                worker = self._r_queue.get()
                self.complete_task(worker, prio=False)

            else:
                worker = self._p_queue.get()
                self.complete_task(worker, prio=True)

    def _start_thread(self):
        self.t = GameThread(target=self._threader)
        self.t.daemon = True
        self.t.start()

    def handlequeue_start(self):
        self.thread_status = True
        self._start_thread()

    def handlequeue_stop(self):
        self.thread_status = False

    def queue_size(self):
        return self._r_queue.qsize() + self._p_queue.qsize()

    def connect(self, host, user, password, db, charset, cursorclass=pymysql.cursors.DictCursor):
        try:
            self.connection = pymysql.connect(host=host,
                                              user=user,
                                              password=password,
                                              db=db,
                                              charset=charset,
                                              cursorclass=cursorclass)
            self.cursor = self.connection.cursor()
            if self._debug:
                print('threaded_mysql: connection was succesfully established.')

            self.connection_method = 1
        except:
            if self._debug:
                print('threaded_mysql: [ERROR] Not possible to make a connection.')

    def connect_use(self, connection):
        try:
            self.connection = connection
            self.cursor = self.connection.cursor()
            if self._debug:
                print('threaded_mysql: [SUCCES] Cursor created succesfully for your connection.')
            self.connection_method = 2
        except:
            if self._debug:
                print('threaded_mysql: [ERROR] Not possible to create cursor.')


    def commit(self):
        """
        Normal pymysql commit
        :return:
        """
        self.connection.commit()

    def close(self, commit_before_save=True):
        """
        Closes the mysql connection
        :param commit_before_save: should it save before closing the connection
        :return:
        """
        if commit_before_save:
            self.connection.commit()

        self.connection.close()










