from __future__ import print_function, division

import inspect
from sympy.core.cache import cacheit
from sympy.core.singleton import S
from sympy.core.sympify import _sympify
from sympy.logic.boolalg import Boolean
from sympy.logic.FOL import Applied, Callable
from sympy.utilities.source import get_class
from contextlib import contextmanager


class AssumptionsContext(set):
    """Set representing assumptions.

    This is used to represent global assumptions, but you can also use this
    class to create your own local assumptions contexts. It is basically a thin
    wrapper to Python's set, so see its documentation for advanced usage.

    Examples
    ========

    >>> from sympy import AppliedPredicate, Q
    >>> from sympy.assumptions.assume import global_assumptions
    >>> global_assumptions
    AssumptionsContext()
    >>> from sympy.abc import x
    >>> global_assumptions.add(Q.real(x))
    >>> global_assumptions
    AssumptionsContext([Q.real(x)])
    >>> global_assumptions.remove(Q.real(x))
    >>> global_assumptions
    AssumptionsContext()
    >>> global_assumptions.clear()

    """

    def add(self, *assumptions):
        """Add an assumption."""
        for a in assumptions:
            super(AssumptionsContext, self).add(a)

global_assumptions = AssumptionsContext()


class AppliedAssumptionsPredicate(Applied):
    """The class of expressions resulting from applying a Predicate.

    Examples
    ========

    >>> from sympy import Q, Symbol
    >>> x = Symbol('x')
    >>> Q.integer(x)
    Q.integer(x)
    >>> type(Q.integer(x))
    <class 'sympy.assumptions.assume.AppliedPredicate'>

    """
    __slots__ = []

    is_Atom = True  # do not attempt to decompose this

    @property
    def arg(self):
        """
        Return the expression used by this assumption.

        Examples
        ========

        >>> from sympy import Q, Symbol
        >>> x = Symbol('x')
        >>> a = Q.integer(x + 1)
        >>> a.arg
        x + 1

        """
        return self._args[0]

    def _eval_ask(self, assumptions):
        return self.func.eval(self.arg, assumptions)

    def _sympystr(self, *args, **kwargs):
        return "Q.%s(%s)" % (self.name, self.arg)


class AssumptionsPredicate(Callable):
    """A predicate is a function that returns a boolean value.

    Predicates merely wrap their argument and remain unevaluated:

        >>> from sympy import Q, ask, Symbol, S
        >>> x = Symbol('x')
        >>> Q.prime(7)
        Q.prime(7)

    To obtain the truth value of an expression containing predicates, use
    the function `ask`:

        >>> ask(Q.prime(7))
        True

    The tautological predicate `Q.is_true` can be used to wrap other objects:

        >>> Q.is_true(x > 1)
        Q.is_true(x > 1)
        >>> Q.is_true(S(1) < x)
        Q.is_true(1 < x)

    """

    is_Atom = True

    def __new__(cls, name, handlers=None):
        return Boolean.__new__(cls)

    def __init__(self, name, handlers=None):
        super(AssumptionsPredicate, self).__init__(name)
        self.handlers = handlers or []

    def __getnewargs__(self):
        return (self.name,)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)

    def apply(self):
        return AppliedAssumptionsPredicate

    def eval(self, expr, assumptions=True):
        """
        Evaluate self(expr) under the given assumptions.

        This uses only direct resolution methods, not logical inference.
        """
        res, _res = None, None
        mro = inspect.getmro(type(expr))
        for handler in self.handlers:
            cls = get_class(handler)
            for subclass in mro:
                try:
                    eval = getattr(cls, subclass.__name__)
                except AttributeError:
                    continue
                res = eval(expr, assumptions)
                if _res is None:
                    _res = res
                elif res is None:
                    # since first resolutor was conclusive, we keep that value
                    res = _res
                else:
                    # only check consistency if both resolutors have concluded
                    if _res != res:
                        raise ValueError('incompatible resolutors')
                break
        return res

    def _sympystr(self, *args, **kwargs):
        return "Q.%s" % self.name


@contextmanager
def assuming(*assumptions):
    """ Context manager for assumptions

    Examples
    ========

    >>> from sympy.assumptions import assuming, Q, ask
    >>> from sympy.abc import x, y

    >>> print(ask(Q.integer(x + y)))
    None

    >>> with assuming(Q.integer(x), Q.integer(y)):
    ...     print(ask(Q.integer(x + y)))
    True
    """
    old_global_assumptions = global_assumptions.copy()
    global_assumptions.update(assumptions)
    try:
        yield
    finally:
        global_assumptions.clear()
        global_assumptions.update(old_global_assumptions)
