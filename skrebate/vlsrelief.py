import numpy as np
import pandas as pd
import time
import warnings
import sys
from sklearn.base import BaseEstimator
from sklearn.base import TransformerMixin
# from sklearn.feature_selection.base import SelectorMixin
from sklearn.externals.joblib import Parallel, delayed
# from .scoring_utils import get_row_missing, ReliefF_compute_scores
from .multisurf import MultiSURF
from .multisurfstar import MultiSURFstar
from .surf import SURF
from .surfstar import SURFstar
from .relieff import ReliefF


class VLSRelief(BaseEstimator, TransformerMixin):

    """Feature selection using data-mined expert knowledge.

    Based on the ReliefF algorithm as introduced in:

    Kononenko, Igor et al. Overcoming the myopia of inductive learning
    algorithms with RELIEFF (1997), Applied Intelligence, 7(1), p39-55

    """

    def __init__(self, core_algorithm, n_features_to_select=2, n_neighbors=100, step=0.1, num_feature_subset=40, size_feature_subset=5, discrete_threshold=10, verbose=False, n_jobs=1):
        """Sets up VLSRelief to perform feature selection.

        Parameters
        ----------
        core_algorithm: Core Relief Algorithm to perform VLSRelief iterations on
        n_features_to_select: int (default: 10)
            the number of top features (according to the relieff score) to
            retain after feature selection is applied.
        step: float/int (default: 0.1)
            If of type float, describes the fraction of features to be removed in each iteration.
            If of type int, describes the number of features to be removed in each iteration.
        discrete_threshold: int (default: 10)
            Value used to determine if a feature is discrete or continuous.
            If the number of unique levels in a feature is > discrete_threshold, then it is
            considered continuous, or discrete otherwise.
        verbose: bool (default: False)
            If True, output timing of distance array and scoring
        n_jobs: int (default: 1)
            The number of cores to dedicate to computing the scores with joblib.
            Assigning this parameter to -1 will dedicate as many cores as are available on your system.
            We recommend setting this parameter to -1 to speed up the algorithm as much as possible.

        """
        self.core_algorithm = core_algorithm
        self.n_features_to_select = n_features_to_select
        self.n_neighbors = n_neighbors
        self.step = step
        self.discrete_threshold = discrete_threshold
        self.verbose = verbose
        self.n_jobs = n_jobs
        self.num_feature_subset = num_feature_subset
        self.size_feature_subset = size_feature_subset

    #=========================================================================#
    # headers = list(genetic_data.drop("class",axis=1))
    def fit(self, X, y, headers):
        """
        Uses the input `core_algorithm` to determine feature importance scores at each iteration.
        At every iteration, a certain number(determined by input parameter `step`) of least important
        features are removed, until the feature set is reduced down to the top `n_features_to_select` features.

        Parameters
        ----------
        X: array-like {n_samples, n_features}
            Training instances to compute the feature importance scores from
        y: array-like {n_samples}
            Training labels
        headers: array-like {n_features}
            Feature names
        Returns
        -------
        Copy of the VLSRelief instance
        """

        self.X_mat = X
        self._y = y
        self.headers = headers

        if self.core_algorithm.lower() == "multisurf":
            core = MultiSURF()

        elif self.core_algorithm.lower() == "multisurfstar":
            core = MultiSURFstar()

        elif self.core_algorithm.lower() == "surf":
            core = SURF()

        elif self.core_algorithm.lower() == "surfstar":
            core = SURFstar()

        elif self.core_algorithm.lower() == "relieff":
            core = ReliefF()

        total_num_features = X.shape[1]
        num_features = self.size_feature_subset
        features_scores_iter = []
        headers_iter = []
        features_selected = []

        for iteration in range(self.num_feature_subset):
            features_selected_id = np.random.choice(
                range(total_num_features), num_features, replace=False)
            self.X_train = self.X_mat[:, features_selected_id]

            core_fit = core.fit(self.X_train, self._y)

            features_scores_iter.append(core_fit.feature_importances_)
            features_selected.append(features_selected_id)
            # headers_iter.append(self.headers[features_selected_id])

        self.features_scores_iter = features_scores_iter
        self.features_selected = features_selected

        zip_feat_score = [list(zip(features_selected[i], features_scores_iter[i]))
                          for i in range(len(features_selected))]
        feat_score = sorted([item for sublist in zip_feat_score for item in sublist])
        feat_score_df = pd.DataFrame(feat_score)
        feat_score_df.columns = ['feature', 'score']
        feat_score_df = feat_score_df.groupby('feature').max().reset_index()

        feature_scores = feat_score_df.values

        feature_scores = [[int(i[0]), i[1]] for i in feature_scores]

        self.feat_score = feature_scores

        head_idx = [i[0] for i in feature_scores]
        self.headers_model = list(np.array(self.headers)[head_idx])

        self.feature_importances_ = [i[1] for i in feature_scores]
        self.top_features_ = np.argsort(self.feature_importances_)[::-1]
        self.header_top_features_ = [self.headers_model[i] for i in self.top_features_]

        return self

    #=========================================================================#

    def transform(self, X):
        """Reduces the feature set down to the top `n_features_to_select` features.

        Parameters
        ----------
        X: array-like {n_samples, n_features}
            Feature matrix to perform feature selection on

        Returns
        -------
        X_reduced: array-like {n_samples, n_features_to_select}
            Reduced feature matrix

        """

        return X[:, self.top_features_[:self.n_features_to_select]]

        # return X[:, self.top_features_]

    #=========================================================================#

    def fit_transform(self, X, y, headers):
        # def fit_transform(self, X, y):
        """Computes the feature importance scores from the training data, then reduces the feature set down to the top `n_features_to_select` features.

        Parameters
        ----------
        X: array-like {n_samples, n_features}
            Training instances to compute the feature importance scores from
        y: array-like {n_samples}
            Training labels

        Returns
        -------
        X_reduced: array-like {n_samples, n_features_to_select}
            Reduced feature matrix

        """
        self.fit(X, y, headers)
        return self.transform(X)
