from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import torch
from gpytorch.kernels import Kernel
from gpytorch.lazy import MatmulLazyTensor, RootLazyTensor
from gpytorch.priors._compatibility import _bounds_to_prior


class LinearKernel(Kernel):
    r"""
    Computes a covariance matrix based on the Linear kernel
    between inputs :math:`\mathbf{x_1}` and :math:`\mathbf{x_2}`:

    .. math::
        \begin{equation*}
            k_\text{Linear}(\mathbf{x_1}, \mathbf{x_2}) = (\mathbf{x_1} - \mathbf{o})^\top
            (\mathbf{x_2} - \mathbf{o}) + v.
        \end{equation*}

    where

    * :math:`\mathbf o` is an :attr:`offset` parameter.
    * :math:`v` is a :attr:`variance` parameter.


    .. note::

        To implement this efficiently, we use a :obj:`gpytorch.lazy.RootLazyTensor` during training and a
        :class:`gpytorch.lazy.MatmulLazyTensor` during test. These lazy tensors represent matrices of the form
        :math:`K = XX^{\top}` and :math:`K = XZ^{\top}`. This makes inference
        efficient because a matrix-vector product :math:`Kv` can be computed as
        :math:`Kv=X(X^{\top}v)`, where the base multiply :math:`Xv` takes only
        :math:`O(nd)` time and space.

    Args:
        :attr:`num_dimensions` (int):
            Number of data dimensions to expect. This
            is necessary to create the offset parameter.
        :attr:`variance_prior` (:class:`gpytorch.priors.Prior`):
            Prior over the variance parameter (default `None`).
        :attr:`offset_prior` (:class:`gpytorch.priors.Prior`):
            Prior over the offset parameter (default `None`).
        :attr:`active_dims` (list):
            List of data dimensions to operate on.
            `len(active_dims)` should equal `num_dimensions`.
    """

    def __init__(
        self,
        num_dimensions,
        variance_prior=None,
        offset_prior=None,
        active_dims=None,
        variance_bounds=None,
        offset_bounds=None,
    ):
        super(LinearKernel, self).__init__(active_dims=active_dims)
        variance_prior = _bounds_to_prior(prior=variance_prior, bounds=variance_bounds, log_transform=False)
        self.register_parameter(name="variance", parameter=torch.nn.Parameter(torch.zeros(1)), prior=variance_prior)
        offset_prior = _bounds_to_prior(prior=offset_prior, bounds=offset_bounds, log_transform=False)
        self.register_parameter(
            name="offset", parameter=torch.nn.Parameter(torch.zeros(1, 1, num_dimensions)), prior=offset_prior
        )

    def forward(self, x1, x2):
        if x1.size() == x2.size() and torch.equal(x1, x2):
            # Use RootLazyTensor when x1 == x2 for efficiency when composing
            # with other kernels
            prod = RootLazyTensor(x1 - self.offset)
        else:
            prod = MatmulLazyTensor(x1 - self.offset, (x2 - self.offset).transpose(2, 1))

        return prod + self.variance.expand(prod.size())
