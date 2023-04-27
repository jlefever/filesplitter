import math
from itertools import chain, pairwise
from functools import cache
from typing import Callable
from collections import Counter

from ordered_set import OrderedSet as oset
import numpy as np
import nltk

STOP_WORDS = {"m", "get", "set", "on", "by", "for", "as", "is", "and", "in", "has"}

def join_singles(terms: list[str]) -> list[str]:
    ret = []
    joined_term = []
    for t in terms:
        if len(t) == 1:
            joined_term.append(t[0])
        elif len(t) > 1:
            if len(joined_term) > 0:
                ret.append("".join(joined_term))
                joined_term = []
            ret.append(t)
    if len(joined_term) > 0:
        ret.append("".join(joined_term))
    return ret


def split_camal(name: str) -> list[str]:
    if name.isupper():
        return [name.lower()]
    indices = [i for i, x in enumerate(name) if x.isupper() or x.isnumeric()]
    indices = [0] + indices + [len(name)]
    return join_singles([name[a:b].lower() for a, b in pairwise(indices)])


def split_identifier(name: str) -> list[str]:
    by_spaces = name.split(" ")
    by_underscores = chain(*(z.split("_") for z in by_spaces))
    return list(chain(*(split_camal(z) for z in by_underscores)))


def termize(name: str) -> list[str]:
    stemmer = nltk.stem.PorterStemmer()
    terms = (stemmer.stem(z) for z in split_identifier(name))
    return [t for t in terms if t not in STOP_WORDS]


def is_noun(term: str) -> bool:
    tags = nltk.pos_tag([term])
    if len(tags) != 1:
        return False
    return tags[0][1].startswith("NN")


def termize2(name: str) -> list[str]:
    stemmer = nltk.stem.PorterStemmer()
    terms = (stemmer.stem(z) for z in split_identifier(name) if is_noun(z))
    return [t for t in terms if t != ""]


def normalize_name(doc: str) -> str:
    return "_".join(termize(doc))


def to_occurrences(doc: str) -> list[tuple[str, str]]:
    normalized = normalize_name(doc)
    return [(t, normalized) for t in termize(doc)]


class NameSimilarity:
    def __init__(self, names: list[str], allow_dup_names: bool = True):
        # Populate a counter for term-document pairs (aka occurrances)
        collect = list if allow_dup_names else set
        pair_counts = Counter(collect(chain(*map(to_occurrences, names))))

        # Populate counters for documents (aka names or identifiers) and terms
        term_counts = Counter(t for t, _ in pair_counts.elements())
        doc_counts = Counter(d for _, d in pair_counts.elements())
        total = pair_counts.total()

        # Define functions for the probabilities and mutual information
        @cache
        def p_i_1(term: str) -> float:
            "Evaluates P(X_i = 1) where i is the term."
            return term_counts[term] / total

        @cache
        def p_i_0(term: str) -> float:
            "Evaluates P(X_i = 0) where i is the term."
            return (total - term_counts[term]) / total

        @cache
        def p_j_1(doc: str) -> float:
            "Evaluates P(Y_j = 1) where j is the document."
            return doc_counts[doc] / total

        @cache
        def p_j_0(doc: str) -> float:
            "Evaluates P(Y_j = 0) where j is the document."
            return (total - doc_counts[doc]) / total

        @cache
        def p_ij_11(term: str, doc: str) -> float:
            "Evaluates P(X_i = 1; Y_j = 1) where i is the term and j is the document."
            return pair_counts[term, doc] / total

        @cache
        def p_ij_10(term: str, doc: str) -> float:
            "Evaluates P(X_i = 1; Y_j = 0) where i is the term and j is the document."
            return (term_counts[term] - pair_counts[term, doc]) / total

        @cache
        def p_ij_01(term: str, doc: str) -> float:
            "Evaluates P(X_i = 0; Y_j = 1) where i is the term and j is the document."
            return (doc_counts[doc] - pair_counts[term, doc]) / total

        @cache
        def p_ij_00(term: str, doc: str) -> float:
            "Evaluates P(X_i = 0; Y_j = 0) where i is the term and j is the document."
            return (total + pair_counts[term, doc] - term_counts[term] - doc_counts[doc]) / total

        def log(x: float) -> float:
            return 0.0 if x == 0.0 else math.log(x)

        def mi(term: str, doc: str) -> float:
            "Evaluates mutual information I(X_i; Y_j) where i is the term and j is the document."
            a = p_ij_11(term, doc) * log(p_ij_11(term, doc) / (p_i_1(term) * p_j_1(doc)))
            b = p_ij_10(term, doc) * log(p_ij_10(term, doc) / (p_i_1(term) * p_j_0(doc)))
            c = p_ij_01(term, doc) * log(p_ij_01(term, doc) / (p_i_0(term) * p_j_1(doc)))
            d = p_ij_00(term, doc) * log(p_ij_00(term, doc) / (p_i_0(term) * p_j_0(doc)))
            return a + b + c + d

        # Create ordered sets for the terms and docs to use as the canonical ordering
        self.terms = oset(term_counts)
        self.docs = oset(doc_counts)

        # Create a rectangular matrix to record I(X_i; Y_j) values
        arr = np.zeros((len(self.terms), len(self.docs)))
        for i, term in enumerate(self.terms):
            for j, doc in enumerate(self.docs):
                arr[i, j] = mi(term, doc)

        # Define positive correlation
        def center(vec: np.ndarray) -> float:
            return vec - np.mean(vec)

        def norm(vec: np.ndarray) -> float:
            return np.linalg.norm(vec)

        def pos_cor(a: np.ndarray, b: np.ndarray) -> float: 
            return max(0, np.dot(center(a), center(b)) / (norm(a) * norm(b)))

        # Create a square matrix to record correlation values
        self.sim_mat = np.zeros((len(self.docs), len(self.docs)))
        for i in range(len(self.docs)):
            for j in range(i, len(self.docs)):
                self.sim_mat[i, j] = self.sim_mat[j, i] = pos_cor(arr[:, i], arr[:, j])
        
        # Create a square dist
        self.dist_mat = 1 - self.sim_mat
    
    def get_doc_ix(self, doc: str) -> int:
        return self.docs.index(normalize_name(doc))

    def sim(self, a_doc: str, b_doc: str) -> float:
        return self.sim_mat[self.get_doc_ix(a_doc), self.get_doc_ix(b_doc)]
    
    def most_sim(self, doc: str, n: int) -> list[tuple[str, float]]:
        doc_ix = self.get_doc_ix(doc)
        most_sim_indices = reversed(np.argsort(self.sim_mat[doc_ix])[-n:-1])
        return [(self.docs[ix], self.sim_mat[doc_ix, ix]) for ix in most_sim_indices]
    
    def dist(self, a_doc: str, b_doc: str) -> float:
        return self.dist_mat[self.get_doc_ix(a_doc), self.get_doc_ix(b_doc)]
