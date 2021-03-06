from __future__ import print_function
import os
import numpy as np
import random
import string
import tensorflow as tf
import zipfile
from six.moves import range
from six.moves.urllib.request import urlretrieve

k = 15000

graph = tf.Graph()
with graph.as_default():
    # Variables
    # Encoder input
    N = tf.placeholder(tf.int32, name="N") #TODO: "extract" value from here
    X = tf.placeholder(tf.float32, shape=[N, k])
    we = tf.Variable(tf.truncated_normal([500, k], -0.1, 0.1))
    # Encoder update gate
    wz = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    uz = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Encoder reset gate
    wr = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    ur = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Encoder h~ [find name]
    w = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    u = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Encoder representation weight
    v = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Decoder representation weight
    v_prime = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Decoder input
    w_prime_e = tf.Variable(tf.truncated_normal([500, k], -0.1, 0.1))
    # Decoder update gate
    w_prime_z = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    u_prime_z = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    Cz = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Decoder reset gate
    w_prime_r = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    u_prime_r = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    Cr = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Decoder h~ [find name]
    w_prime = tf.Variable(tf.truncated_normal([1000, 500], -0.1, 0.1))
    u_prime = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    C = tf.Variable(tf.truncated_normal([1000, 1000], -0.1, 0.1))
    # Decoder maxout calculation
    oh = tf.Variable(tf.truncated_normal([2000, 1000], -0.1, 0,1))
    oy = tf.Variable(tf.truncated_normal([2000, 1000], -0.1, 0, 1))
    oc = tf.Variable(tf.truncated_normal([2000, 1000], -0.1, 0, 1))
    # Decoder output
    gl = tf.Variable(tf.truncated_normal([k, 500], -0.1, 0, 1))
    gr = tf.Variable(tf.truncated_normal([500, 1000], -0.1, 0, 1))

    # Encoder
    h_previous = tf.zeros([1000])
    for t in range(N):
        # Current vector and its embedding
        xt = tf.reshape(tf.slice(N, [t, 0], [1, k]), [k])
        e = tf.matmul(we, xt)
        # Vectors for reset calculation
        wr_e = tf.matmul(wr, e)
        ur_ht_previous = tf.matmul(ur, h_previous)
        # Vectors for update calculation
        wz_e = tf.matmul(wz, e)
        uz_ht_previous = tf.matmul(wz, h_previous)

        # Reset calculation
        r = tf.zeros([1000])
        for j in range(1000):
            j = j + 1
            rj = tf.sigmoid(tf.slice(wr_e, [j], [1]) + tf.slice(ur_ht_previous, [j], [1]))
            r = r + tf.sparse_tensor_to_dense(tf.SparseTensor([j], [rj], [1000]))

        # Vectors for h~ calculation
        w_e = tf.matmul(w, e)
        r_ewm_h_previous = tf.zeros([1000])
        for j in range (1000):
            j = j + 1
            ewm = tf.slice(r, [j], [1]) * tf.slice(h_previous, [j], [1])
            r_ewm_h_previous = r_ewm_h_previous + tf.sparse_tensor_to_dense(tf.SparseTensor([j], [ewm], [1000]))
        u_r_ewm_h_previous = tf.matmul(u, r_ewm_h_previous)

        # Hidden calculation
        h = tf.zeros([1000])
        for j in range(1000):
            j = h + 1
            #Update calculation
            zj = tf.sigmoid(tf.slice(wz_e, [j], [1]) + tf.slice(uz_ht_previous, [j], [1]))
            #h~ calculation
            hj_tilde = tf.tanh(tf.slice(w_e, [j], [1]) + tf.slice(u_r_ewm_h_previous, [j], [1]))

            hj = zj*tf.slice(h_previous, [j], [1]) + (1-zj)*hj_tilde
            h = h + tf.sparse_tensor_to_dense(tf.SparseTensor([j], [hj], [1000]))

        h_previous = h
    c = tf.tanh(tf.matmul(v, h_previous))

    # Decoder
    continue_sentence = True
    y_previous = tf.zeros([k])
    h_prime_previous = tf.tanh(tf.matmul(v_prime, c))
    while (continue_sentence): #TODO: while y_previous is not EOS
        # Current vector's embedding
        e = tf.matmul(w_prime_e, y_previous)
        # Vectors for h~ calculation
        w_e = tf.matmul(w_prime, e)
        u_h_previous = tf.matmul(u_prime, h_prime_previous)
        C_c = tf.matmul(C, c)
        # Vectors for reset calculation
        wr_e = tf.matmul(w_prime_r, e)
        ur_ht_previous = tf.matmul(u_prime_r, h_previous)
        Cr_c = tf.matmul(Cr, c)
        # Vectors for update calculation
        wz_e = tf.matmul(w_prime_z, e)
        uz_ht_previous = tf.matmul(w_prime_z, h_previous)
        Cz_c = tf.matmul(Cz, c)

        # Hidden calculation
        h_prime = tf.zeros([1000])
        for j in range(1000):
            j = j + 1
            r_prime_j = tf.sigmoid(tf.slice(wr_e, [j], [1]) + tf.slice(u_h_previous, [j], [1])
                                   + tf.slice(Cr_c, [j], 1))
            z_prime_j = tf.sigmoid(tf.slice(wz_e, [j], [1]) + tf.slice(uz_ht_previous, [j], [1])
                                   + tf.slice(Cz_c, [j], [1]))
            h_prime_j_tilde = tf.tanh(tf.slice(w_e, [j], [1]) + r_prime_j * tf.slice(u_h_previous + C_c, [j], [1]))
            h_prime_j = z_prime_j*tf.slice(h_prime_previous, [j], [1]) + (1-z_prime_j)*h_prime_j_tilde
            h_prime = h_prime + tf.sparse_tensor_to_dense(tf.SparseTensor([j], [h_prime_j], [1000]))

        # Maxout calculation
        s_prime = tf.matmul(oh, h_prime) + tf.matmul(oy, y_previous) + tf.matmul(oc, c)
        s = tf.zeros([1000])
        for i in range(1000):
            i = i + 1
            s_i = max(tf.slice(s, [2*i-1], [1]), tf.slice(s, [2*i], [1])) #TODO: fix this, this is almost certainly wrong
            s = s + tf.sparse_tensor_to_dense(tf.SparseTensor([i], [s_i], [1000]))

        # Softmax calculation
        g = tf.matmul(gl, gr)
        denominator = tf.zeros([1])
        softmax = tf.zeros([k])
        for j in range(k):
            j = j + 1
            g_j = tf.reshape(tf.slice(g, [j, 0], [1, 1000]), [1, 1000])
            e_g_j_s = tf.exp(tf.matmul(g_j, s))
            softmax = softmax + tf.sparse_tensor_to_dense(tf.SparseTensor([j], [e_g_j_s], [1000]))
            denominator = denominator + tf.sparse_tensor_to_dense(tf.SparseTensor([1], [e_g_j_s], [1000]))
        softmax = tf.matmul(softmax, tf.inverse(denominator))

        h_prime_previous = h_prime