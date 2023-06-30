First, define some basic notation.

- Let $D$ be the set of documents (identifiers) and let $T$ be the set of terms.

- Let $S \subseteq T \times D$ be the set of term-document occurrences (or _sample points_.) If `allow_dup_docs = True`, then $S$ is a multi-set.

Next, define some useful subsets.

- Let $S_i = \{s : s = (t,d) \in S \text{ and } t=t_i\}$ be the subset of occurrences that contain term $t_i$.

- Let $S_j = \{s : s = (t,d) \in S \text{ and } d=d_j\}$ be the subset of occurrences that contain document $d_j$.

- Let $S_{ij} = \{s : s = (t,d) \in S \text{ and } t=t_i \text{ and } d=d_j\}$ be the subset of occurrences that contain both term $t_i$ and document $d_j$.

And some useful shorthand for refering the size of these subsets.

- Let $c = |S|$ be the number of term-document pairs.

- Let $c_i = |S_i|$ be the number of documents that contain term $t_i$.

- Let $c_j = |S_j|$ be the number of terms that are contained within document $d_j$.

- Let $c_{ij} = |S_{ij}|$ be the number of times term $t_i$ is used by document $d_j$.

Now define some random variables.

- Let $X_i(s)$ for some $s = (t, d) \in S$ be the indicator random variable $\mathbf{1}_{S_i}$.

- Let $Y_j(s)$ for some $s = (t, d) \in S$ be the indicator random variable $\mathbf{1}_{S_j}$.

If we assume each sample point $s \in S$ is equiprobable, we can find these joint probability distributions.

- $P(X_i = 1; Y_j = 1) = p_{ij}(1,1) = c_{ij}/c$

- $P(X_i = 1; Y_j = 0) = p_{ij}(1,0) = (c_i - c_{ij}) / c$

- $P(X_i = 0; Y_j = 1) = p_{ij}(0,1) = (c_j - c_{ij}) / c$

- $P(X_i = 0; Y_j = 0) = p_{ij}(0,0) = (c + c_{ij} - c_i - c_j) / c$

And then the marginals.

- $P(X_i = 1) = p_{i}(1) = c_i / c$

- $P(X_i = 0) = p_{i}(0) = 1 - c_i / c = (c - c_i) / c$

- $P(Y_j = 1) = p_{j}(1) = c_j / c$

- $P(Y_j = 0) = p_{j}(0) = 1 - c_j / c = (c - c_j) / c$

Now we can calculate the mutual information between any $X_i$ and $Y_j$.

$$
I(X_i;Y_j)
=
\sum_{y \in \{0,1\}}\sum_{x \in \{0,1\}}
P(X_i = x; Y_j = y)
\log{\left(\frac{P(X_i = x; Y_j = y)}{P(X_i = x)P(Y_j = y)}\right)}
$$
