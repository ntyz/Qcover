import itertools
import os
import time
import warnings
from collections import defaultdict, Callable
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Pool, cpu_count
import quimb as qu
from multiprocessing import cpu_count
from Qcover.backends import Backend


class CircuitByTensor(Backend):
    """generate a instance of tensor network circuit generated by quimb"""

    def __init__(self,
                 nodes_weight: list = None,
                 edges_weight: list = None,
                 contract_opt: str = 'greedy',
                 is_parallel: bool = None) -> None:

        """initialize a instance of tensor network circuit:"""

        super(CircuitByTensor, self).__init__()
        self._p = None
        self._nodes_weight = nodes_weight
        self._edges_weight = edges_weight
        self._is_parallel = False if is_parallel is None else is_parallel
        self._opt = contract_opt

        self._element_to_graph = None
        self._pargs = None
        self._expectation_path = []

    def get_operator(self, element, qubit_num):
        pass

    def get_expectation(self, element_graph, p=None):
        if self._is_parallel is False:
            p = self._p if p is None else p
            original_e, graph = element_graph
        else:
            p = self._p if len(element_graph) == 1 else element_graph[1]
            original_e, graph = element_graph[0]

        node_to_qubit = defaultdict(int)
        node_list = list(graph.nodes)
        for i in range(len(node_list)):
            node_to_qubit[node_list[i]] = i

        gamma_list, beta_list = self._pargs[: p], self._pargs[p:]
        circ = qu.tensor.Circuit(len(graph.nodes))

        for k in range(p):
            for nd in graph.nodes:
                u = node_to_qubit[nd]
                if k == 0:
                    circ.apply_gate('H', u)
                circ.apply_gate('rz', 2 * gamma_list[k] * self._nodes_weight[nd], u)

            for edge in graph.edges:
                u, v = node_to_qubit[edge[0]], node_to_qubit[edge[1]]
                if u == v:
                    continue
                circ.apply_gate('RZZ', -gamma_list[k] * self._edges_weight[edge[0], edge[1]], u, v)

            for nd in graph.nodes:
                circ.apply_gate('rx', 2 * beta_list[k], node_to_qubit[nd])

        if isinstance(original_e, int):
            weight = self._nodes_weight[original_e]
            where = node_to_qubit[original_e]
            exp_res = circ.local_expectation(qu.pauli('Z'), where, optimize=self._opt)
        else:
            weight = self._edges_weight[original_e]
            ZZ = qu.pauli('Z') & qu.pauli('Z')
            where = (node_to_qubit[original_e[0]], node_to_qubit[original_e[1]])
            exp_res = circ.local_expectation(ZZ, where, optimize=self._opt)
        return exp_res.real * weight

    def expectation_calculation(self, p=None):
        if self._is_parallel:
            return self.expectation_calculation_parallel(p)
        else:
            return self.expectation_calculation_serial(p)

    def expectation_calculation_serial(self, p=None):
        cpu_num = cpu_count()
        os.environ['OMP_NUM_THREADS'] = str(cpu_num)
        os.environ['OPENBLAS_NUM_THREADS'] = str(cpu_num)
        os.environ['MKL_NUM_THREADS'] = str(cpu_num)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(cpu_num)
        os.environ['NUMEXPR_NUM_THREADS'] = str(cpu_num)
        res = 0
        for item in self._element_to_graph.items():
            res += self.get_expectation(item, p)

        print("Total expectation of original graph is: ", res)
        self._expectation_path.append(res)
        return res

    def expectation_calculation_parallel(self, p=None):
        cpu_num = 1
        os.environ['OMP_NUM_THREADS'] = str(cpu_num)
        os.environ['OPENBLAS_NUM_THREADS'] = str(cpu_num)
        os.environ['MKL_NUM_THREADS'] = str(cpu_num)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(cpu_num)
        os.environ['NUMEXPR_NUM_THREADS'] = str(cpu_num)

        circ_res = []
        args = list(itertools.product(self._element_to_graph.items(), [p]))
        pool = Pool(os.cpu_count())
        circ_res.append(pool.map(self.get_expectation, args))
        # circ_res.append(pool.map(self.get_expectation, list(self._element_to_graph.items()), chunksize=1))

        pool.terminate()  # pool.close()
        pool.join()

        res = sum(circ_res[0])
        print("Total expectation of original graph is: ", res)
        self._expectation_path.append(res)
        return res

    def visualization(self):
        plt.figure()
        plt.plot(range(1, len(self._expectation_path) + 1), self._expectation_path, "ob-", label="quimb")
        plt.ylabel('Expectation value')
        plt.xlabel('Number of iterations')
        plt.legend()
        plt.show()

