from threading import Thread
import time
import uuid

class Queue:
    def __init__(self):
        self.queue = {}

    def push(self, uid, element):
        self.queue[uid] = element

    def pop(self, uid=0):
        if uid in self.queue:
            return self.queue.pop(uid)
        else:
            return None

    def get(self, uid):
        if uid in self.queue:
            return self.queue[uid]
        else:
            return None

    def wait(self, timeout=1e9):
        loop_time = 0
        delta = 0.1
        while len(self.queue) == 0 and loop_time < timeout:
            time.sleep(delta)
            loop_time += delta
        return True

    def available_uid(self):
        return set(self.queue.keys())

    def __len__(self):
        return len(self.queue)

    def __contains__(self, item):
        return item in self.queue


class PlaceHolder:
    def __init__(self):
        self.queue = Queue()

    def eval(self, uid=None):
        self.queue.wait()
        return self.queue.get(uid)

    def add(self, uid, element):
        self.queue.push(uid, element)

    def available_uid(self):
        return self.queue.available_uid()


class Node(Thread):
    def __init__(self, func, *args, **kwargs):
        Thread.__init__(self)
        self.inputs = [arg for arg in args if hasattr(arg, 'eval')] + [arg for arg in kwargs.values() if
                                                                       hasattr(arg, 'eval')]
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.delta = 0
        self.outputs = Queue()

    def eval(self, uid=None):
        if uid in self.outputs.available_uid():
            print('available in queue')
            return self.outputs.get(uid)
        args = [arg.eval(uid) if hasattr(arg, 'eval') else arg for arg in self.args]
        kwargs = {k: arg.eval(uid) if hasattr(arg, 'eval') else arg for k, arg in self.kwargs.items()}
        output = self.func(*args, **kwargs)
        self.outputs.push(uid, output)
        return output

    def check_input(self):
        if len(self.inputs) == 0:
            return [uuid.uuid4().hex]
        uid_available = self.inputs[0].available_uid()
        for input_node in self.inputs[1:]:
            uid_available &= input_node.available_uid()

        if len(uid_available) == 0:
            return None
        else:
            return sorted([uid for uid in uid_available if uid not in self.outputs.available_uid()])

    def available_uid(self):
        return self.outputs.available_uid()

    def run(self):
        print('start process')
        self.__stop = False
        while not self.__stop:
            uids = self.check_input()
            if uids:
                for uid in uids:
                    self.eval(uid)
                    if self.delta > 0:
                        time.sleep(self.delta)
            else:
                time.sleep(0.01)

    def stop(self):
        self.__stop = True


class Layer:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        node = Node(self.func, *args, **kwargs)
        return node


def get_node(node):
    nodes = []
    if isinstance(node, Node):
        for input_node in node.inputs:
            nodes.append(input_node)
            nodes.extend(get_node(input_node))
    return nodes

def get_graph(node):
    edges = []
    if isinstance(node,Node):
        for input_node in node.inputs:
            edges.append([id(input_node),id(node)])
            edges.extend(get_graph(input_node))
    return edges


class Graph:
    def __init__(self, target, inputs=None):
        self.nodes = get_node(target)
        self.nodes.append(target)
        self.edges = get_graph(target)
        self.target = target
        if inputs is None:
            self.inputs = [node for node in self.nodes if isinstance(node, PlaceHolder)]
        else:
            self.inputs = inputs
        self.nodes = [node for node in self.nodes if isinstance(node, Node)]

    def start(self):
        for node in self.nodes:
            if isinstance(node, Node):
                node.start()

    def stop(self):
        for node in self.nodes:
            if isinstance(node, Node):
                node.stop()

    def add_input(self, uid, args):
        for arg, node in zip(args, self.inputs):
            node.add(uid, arg)

    def get_output(self):
        return self.nodes[-1].outputs.queue

    def run_one(self, *args):
        uid = uuid.uuid4().hex
        self.add_input(uid, args)
        return self.target.eval(uid)

    def balance(self):
        self.check_balance = True
        while self.check_balance:
            avg_len = sum(len(node.outputs) for node in self.nodes) / len(self.nodes)
            for node in self.nodes:
                if len(node.outputs) > 1.1 * avg_len:
                    node.delta += 0.01 * (len(node.outputs) - avg_len)
                elif len(node.outputs) < avg_len:
                    node.delta = 0
            time.sleep(0.2)

    def run_batch(self, batch):
        start = time.time()
        self.start()
        Thread(target=self.balance).start()
        sequence = []
        uid = 0
        for args in batch:
            uid += 1
            self.add_input(uid, args)
            sequence.append(uid)
        time_response = []
        for uid in sequence:
            i_start = time.time()
            yield self.target.eval(uid)
            time_response.append(time.time() - i_start)
        self.check_balance = False
        self.stop()
        print('min reponse', min(time_response))
        print('avg reponse', sum(time_response) / len(time_response))
        print('max reponse', max(time_response))
        print('done', time.time() - start)
