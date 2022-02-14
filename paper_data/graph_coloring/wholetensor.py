import os
from Qcover.applications.graph_color import GraphColoring
from time import time
import numpy as np
import h5py
import quimb as qu
import quimb.tensor as qtn
from scipy.optimize import minimize, rosen_der


def qaoa_tensor(graph, p, params):

    N = len(graph.nodes)
    circ = qu.tensor.Circuit(N)

    for i in graph.nodes():
        circ.apply_gate('H', i)

    for k in range(p):
        for i in graph.nodes:
            node_weight = graph.nodes[i]['weight']
            circ.apply_gate('rz', 2 * params[2 * k] * node_weight, i)

        for edge in graph.edges:
            edge_weight = graph.get_edge_data(edge[0], edge[1])['weight']

            gamma = -params[2 * k] * edge_weight
            circ.apply_gate('RZZ', gamma, edge[0], edge[1])

        for i in graph.nodes:
            circ.apply_gate('rx', 2 * params[2 * k + 1], i)
    return circ

def expectation(mx_g, circ, opt):
    expectation = 0
    ZZ = qu.pauli('Z') & qu.pauli('Z')
    for node in mx_g.nodes:
        # warning
        w = mx_g.nodes[node]['weight']
        expectation = w * circ.local_expectation(qu.pauli('Z'), node, optimize=opt) + expectation

    for edge in mx_g.edges:
        # warning
        w = mx_g.get_edge_data(edge[0], edge[1])['weight']
        expectation = w * circ.local_expectation(ZZ, edge, optimize=opt) + expectation
    return expectation.real

def energy(params, mx_g, p,opt):
    circ = qaoa_tensor(mx_g, p, params)
    expec = expectation(mx_g, circ,opt)
    return expec

p = 1
opt = 'greedy'
# num_nodes_list = np.arange(10,500,40)
num_nodes_list = np.array([4,6])
cln = 3
nd = 3
time_tensor = np.zeros(len(num_nodes_list), dtype=float)
exp_tensor = np.zeros_like(time_tensor) #expectation value
parametr_f_tensor = np.zeros([len(num_nodes_list),2, p], dtype=float)
cy_ind = 0
max_step = 1
for num_nodes in num_nodes_list:
    gct = GraphColoring(node_num=num_nodes, color_num=cln, node_degree=nd) 
    ising_g = gct.run()
    gamma = np.random.rand(p)
    beta = np.random.rand(p)

    st = time()
    qser_whole_tensor = minimize(energy, np.asarray([gamma, beta]), args=(ising_g, p,opt),
                           method='COBYLA',
                           tol=1e-14,
                           jac=rosen_der,
                           options={'gtol': 1e-8, 'maxiter': max_step, 'disp': True})
    time_tensor[cy_ind] = time() - st
    exp_tensor[cy_ind] = qser_whole_tensor.fun
    parametr_f_tensor[cy_ind,0,:] = qser_whole_tensor.x[0,:]
    parametr_f_tensor[cy_ind,1,:] = qser_whole_tensor.x[1,:]

    cy_ind += 1

dirs = '../data'
if not os.path.exists(dirs):
    os.makedirs(dirs)

if len(num_nodes_list) == 1:
    filename = '../data/graphcolor_wtensor_p%i_nodesnum%i_nd%i_cln%i.h5'%(p, num_nodes_list[0],nd,cln)
else:
    filename = '../data/graphcolor_wtensor_p%i_nd%i_cln%i.h5'%(p,nd,cln)
data = h5py.File(filename, 'w')
data['time_tensor'] = time_tensor
data['exp_tensor'] = exp_tensor
data['parametr_f_tensor'] = parametr_f_tensor
data['num_nodes_list'] = num_nodes_list
data['maxiter'] = max_step
data['p'] = p
data['nd'] = nd
data['cln'] = cln
data.close()






