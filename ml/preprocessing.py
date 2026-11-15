"""Train-fold preprocessing and small CPU regressors, including an abstaining baseline."""

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import QhullError
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class LocalLinearInterpolation(RegressorMixin, BaseEstimator):
    """No extrapolation, and no invented value when a convex interpolation is not defined."""

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        self.origin_ = X[0]
        self.active_ = np.ptp(X, axis=0) > 1e-12
        self.points_ = X[:, self.active_]
        self.y_ = np.asarray(y)
        self.interpolator_ = None
        if self.points_.shape[1] > 1:
            try:
                self.interpolator_ = LinearNDInterpolator(self.points_, self.y_)
            except (QhullError, ValueError):
                pass
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        points = X[:, self.active_]
        result = np.full(len(X), np.nan)
        # Changing a constant training coordinate leaves the measured affine subspace.
        valid = np.all(np.isclose(X[:, ~self.active_], self.origin_[~self.active_], atol=1e-10), axis=1)
        if points.shape[1] == 1:
            order = np.argsort(self.points_[:, 0])
            xs = self.points_[order, 0]
            ys = self.y_[order]
            # Different outcomes at the same coordinate do not define a unique interpolation.
            if len(np.unique(xs)) == len(xs):
                result[valid] = np.interp(points[valid, 0], xs, ys, left=np.nan, right=np.nan)
        elif self.interpolator_ is not None:
            result[valid] = self.interpolator_(points[valid])
        return result


def candidates(task):
    seed = task["seed"]
    models = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "linear_interpolation": LocalLinearInterpolation(),
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=200, min_samples_leaf=2, max_features=1.0,
                                               n_jobs=1, random_state=seed),
        "gaussian_process": GaussianProcessRegressor(
            kernel=ConstantKernel(1.0, (0.01, 100)) * Matern(length_scale=1.0, nu=1.5)
                   + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 10)),
            normalize_y=True, random_state=seed, n_restarts_optimizer=1),
        "mlp": TransformedTargetRegressor(
            regressor=MLPRegressor(hidden_layer_sizes=(8,), activation="tanh", solver="lbfgs",
                                   alpha=0.1, max_iter=3000, random_state=seed),
            transformer=StandardScaler()),
    }
    return {name: Pipeline([
        ("features", ColumnTransformer([
            ("numeric", StandardScaler(), task["numeric_features"]),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), task["categorical_features"]),
        ])),
        ("model", model),
    ]) for name, model in models.items()}
