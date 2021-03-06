# -*- coding: utf-8 -*-
"""hot_topixx.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1QToCk4V1spL9jaPbNYAIEzm8kJMeccjw9b
"""

import numpy as np
# import scipy
# import matplotlib.pyplot as plt

"""# Initialize random X
"""

def initialize_matrix(f, n, fixed_parts=None):
    """
    Initializes a random matrix X of size (f,n)
    Args:
        f,n (int): dimension of output matrix

    Returns:
        X: a random matrix of size (f,n)
    """
    if fixed_parts is None:
        ans = np.random.rand(f,n)
        return ans/ans.sum(axis=1, keepdims=True)

    # Trim num of fixed rows
    assert(fixed_parts.shape[1]==n and fixed_parts.shape[0]<=f), "fixed_parts has incompatible size!"

    # Normalize fixed_parts
    fixed_parts = fixed_parts/fixed_parts.sum(axis=1, keepdims=True)

    # Generate the remaining rows as convex conbination of the first rows
    weights = np.random.rand(f-fixed_parts.shape[0], fixed_parts.shape[0])
    weights = weights/weights.sum(axis=1, keepdims=True)
    temp = np.matmul(weights, fixed_parts)

    # Combing these with X
    return np.concatenate([fixed_parts, temp], axis=0)


def proj_on_Phi0(arr, max_index, f):
    """
    Project a vector arr onto \Phi_0, such that max index occurs at max_index
    This is Algorithm "column squishing" algorithm in reference

    Args:
        arr (numpy 1d array)
        max_index (int): index where maximum happens
        f (int): number of features in X matrix

    Returns:
        projection of arr onto Phi_0 space
    """

    # Sort arr except for position max_index
    temp = arr[max_index]
    arr[max_index] = np.nan
    arr = np.sort(arr)[::-1]
    arr[0] = temp

    # Initialize ans
    ans = np.zeros_like(arr)

    # Apply column squishing algorithm
    k_c = f-1
    mu = clip(temp)
    for k in range(1,f):
        if arr[k] <= mu:
            k_c = k-1
            break
        mu = clip(1/(k+1)*(k*mu + arr[k]))

    ans[0:k_c+1] = mu
    ans[k_c+1:] = np.maximum(arr[k_c+1:], 0)

    # Correct for the re-indexing
    #   x_1 is maximum as for now, but we want x[max_index] to be maximum
    if ans[max_index] == mu:
        return ans

    ans[0] = ans[max_index]
    ans[max_index] = mu
    return ans


def adam(grad_c, C, moment, velocity, s_p,
         coef_1, coef_2, coef_1_pow, coef_2_pow, eps, update_pow=True):
    """
    Adam algorithm for optimization.

    Args:
        grad_c (np array): same size as the parameter to be optimized (in our case, matrix C)
        C (np array): matrix to be optimized (in our case, matrix of size (f,f))
        moment (np array): moment in Adam algorith, same dimension as C
        velocity (np array): velocity in Adam algorith, same dimension as C
        s_p (double): learning rate
        coef_1 (double): beta_1 in Adam algorithm, discount for moment
        coef_2 (double): beta_2 in Adam algorithm, discount for velocity
        coef_1_pow (double): coef_1**iter, saved to speed up
        coef_2_pow (double): coef_2**iter, saved to speed up
        eps (double): epsilon to avoid singularity in division

    Returns:
        C, moment, velocity, coef_1_pow, coef_2_pow after one iteration in Adam algorithm. Same definition as in Args.

    """
    moment = coef_1 * moment + (1-coef_1) * grad_c
    velocity = coef_2 * velocity + (1-coef_2) * np.square(grad_c)
    grad_c = np.divide(1/(1-coef_1_pow)*moment, eps+np.sqrt(velocity/(1-coef_2_pow)))
    C -= s_p * grad_c
    if update_pow:
        coef_1_pow = coef_1_pow * coef_1
        coef_2_pow = coef_2_pow * coef_2
    return C, moment, velocity, coef_1_pow, coef_2_pow


def clip(mat):
    """
    Project onto interval [0,1]
    """
    mat = np.maximum(mat, 0)
    mat = np.minimum(mat, 1)
    return mat



def find_C(X, r, stopping_criterion=None,
           EPOCHS=20, s_p=.01, s_d=.01, coef_1=.9, coef_2=.999, eps=1e-8):
    """
    Find C matrix in HOTTOPIXX algorithm

    Args:
        X (np array): dimension (f,n), data matrix
        r (int): num of boundary vectors to be found
        EPOCHS (int): maximum iteration allowed
        stopping_criterion (callable): a function that returns whether or not
                                       to stop iteration
        s_p (double): learning rate for C
        s_d (double): learning rate for beta
        coef_1 (double): discount rate in Adam optimization
        coef_2 (double): discount rate in Adam optimization
        eps (double): normalization to avoid singularity in Adam optimization

    Returns:
        C (np array) as in HOTTOPIXX algorithm
    """

    # Initialize parameters
    f,n = X.shape[0], X.shape[1]
    C = np.zeros([f,f])
    p = np.diag(np.random.rand(f))
    moment = np.zeros_like(C)
    velocity = np.zeros_like(C)
    beta = 0
    coef_1_pow = coef_1
    coef_2_pow = coef_2
    moment_beta = 0
    velocity_beta = 0
    iter = 0
    early_stopping = False

    while iter < EPOCHS and (not early_stopping):
        CHOICES = np.random.choice(n, size=n)
        for i in range(n):
            k = CHOICES[i]
            X_k = X[:,k].reshape(-1,1)
            # Compute gradient of C
            grad_c = -np.matmul(np.sign(X_k - np.matmul(C, X_k)),
                               X[:,k].reshape(1,-1))
            grad_c += beta-np.diag(p)
            C, moment, velocity, coef_1_pow, coef_2_pow = \
                adam(grad_c, C, moment, velocity, s_p, coef_1, coef_2, coef_1_pow, coef_2_pow, eps)

        # Project onto Phi_0
        for j in range(f):
            C[j,:] = proj_on_Phi0(C[j,:], j, f)

        # Determine early stopping
        temp = np.partition(-np.diagonal(C), r)
        tr_C = np.trace(C)
        err1, err2, err3 = -np.mean(temp[:r]), np.abs(np.mean(temp[r:])), beta*np.abs(tr_C-r)
        print(err1, err2, err3)
        early_stopping = stopping_criterion(err1, err2, err3)
        # Update beta
        beta += s_d * (tr_C-r)
        # beta, moment_beta, velocity_beta, coef_1_pow, coef_2_pow = \
        #     adam(tr_C-r, beta, moment_beta, velocity_beta, s_d, coef_1,
        #          coef_2, coef_1_pow, coef_2_pow, False)
        iter += 1
    return C, iter

def stopping_criterion(err1, err2, err3):
    """
    Stopping criterion for find_C
    """
    if np.abs(err1) - np.abs(err2) > .5:
        return True
    return False


# Sample call to the functions
def main():
    f = 10
    n = 4
    r = 2
    # BDRY_ROWS = np.random.rand(n,n)
    BDRY_ROWS = np.array([[.1,.1,.8,0.],
                          [.1,.8,0.,.1],
                          [.8,.1,0.,.1]])
    X = initialize_matrix(f, n, BDRY_ROWS)

    print("X matrix ============================")
    print(X)

    C, iter = find_C(X, r, stopping_criterion, 30)
    print("***\nConcluded after {} iterations!!!\n***".format(iter))


    print("\nC matrix ============================")
    print(np.diagonal(C))
    print("\n Diff matrix ============================")
    print(X-np.matmul(C,X))

main()
