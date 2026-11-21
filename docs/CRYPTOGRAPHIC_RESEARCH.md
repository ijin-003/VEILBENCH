# MPyC Cryptographic Research and Validation Report
**Project:** VEILBENCH — Secure Multiparty Benchmarking  
**Milestone:** Prompt 1 — Cryptographic Research & Framework Verification  
**Author:** Cryptographic Systems Engineering Team  
**Framework:** MPyC (Secure Multi-Party Computation in Python by Berry Schoenmakers)  

---

## 1. Overview of MPyC Architecture & Shamir MPC

MPyC is an open-source Python framework designed for multi-party computation based on Shamir's threshold secret sharing scheme and asynchronous I/O (`asyncio`). 

### 1.1 How MPyC Implements Shamir-Based MPC
- **Threshold Scheme**: Operates over finite fields $\mathbb{F}_p$ or Galois extensions $\mathbb{F}_{p^k}$. Every secret $s$ is shared by sampling a random polynomial $f(x) \in \mathbb{F}_p[x]$ of degree at most $t$, such that $f(0) = s$.
- **Parties & Threshold**:
  - $m$: Number of compute parties.
  - $t$: Corruption threshold. By default, MPyC sets $t = \lfloor (m-1)/2 \rfloor$.
  - For $m = 3$, $t = 1$. A degree-$1$ polynomial is used: $f(x) = s + a_1 x \pmod p$.
- **Homomorphic Linearity**: Linear operations (addition, subtraction, public scalar multiplication) are executed **entirely locally** by each party on their respective shares without network rounds:
  $$[s_1 + s_2]_i = [s_1]_i + [s_2]_i$$
  $$[c \cdot s]_i = c \cdot [s]_i$$

### 1.2 How Secure Input Works (`mpc.input`)
MPyC provides the asynchronous method `mpc.input(x, senders=None)`:
- If a party is the designated sender ($i = \text{senders}$), it supplies its private value wrapped in a secure type: `secint(salary)`.
- All other parties provide a type placeholder or `None`.
- Under the hood: The sender samples $t$ random field elements $a_1, \dots, a_t \xleftarrow{\$} \mathbb{F}_p$, computes shares $[s]_j = f(x_j)$ for all $j \in \{0, \dots, m-1\}$, and transmits share $[s]_j$ to party $j$ over peer-to-peer TCP channels.
- When `senders=None` or is a list, every party can provide their input concurrently:
  ```python
  shares = mpc.input(secint(my_salary))  # returns [share_0, share_1, share_2]
```

### 1.3 How Secret Integers are Represented (`SecInt`)
- `secint = mpc.SecInt(l=32)` creates a secure integer class with $l$-bit precision.
- MPyC automatically instantiates an underlying prime field $\mathbb{F}_p$ such that $p > 2^l \cdot m$ to prevent modular overflow during linear combinations.
- A `SecInt` object holds an `asyncio.Future` resolving to a share in $\mathbb{F}_p$. Overloaded operators (`+`, `-`, `*`) compose computation graphs transparently.

### 1.4 How Secure Summation is Performed
- Secure summation of 3 parties' inputs $[s_0], [s_1], [s_2]$:
  ```python
  total_share = sum(shares)  # Equivalent to shares[0] + shares[1] + shares[2]
```
- **Zero Inter-Party Network Rounds**: Each party $j$ simply computes:
  $$[S]_j = [s_0]_j + [s_1]_j + [s_2]_j \pmod p$$
  No communication is required for the addition step.

### 1.5 How Output Reconstruction Works (`mpc.output`)
- `await mpc.output(total_share)` triggers the reconstruction phase:
  1. Each party broadcasts its local aggregate share $[S]_j$ to all other parties (or to a designated subset).
  2. Each party gathers the shares and evaluates Lagrange basis polynomials at $x=0$:
     $$S = \sum_{j=0}^{m-1} [S]_j \cdot \ell_j(0) \pmod p$$
  3. The cleartext integer $S$ is returned.
- For calculating the average:
  $$\text{Average} = \frac{S}{3}$$
  Because division by the public constant 3 is performed on the reconstructed sum, the exact average is obtained with zero extra cryptographic overhead.

### 1.6 Party Configuration & Network Options
- **Command Line Flags**:
  - `-M m`: Sets total number of parties (e.g., `-M 3`).
  - `-I i`: Sets current party ID ($0 \le i < m$, e.g., `-I 0`).
  - `-T t`: Sets threshold $t$ (e.g., `-T 1`).
  - `-P addr`: Party addresses (`host:port`).
  - `-C path`: Configuration file defining party hostnames and ports.
- **TLS Configuration**:
  - `--ssl`: Activates TLS encryption for all peer-to-peer sockets.
  - MPyC looks for certificates and keys (`party_i.crt`, `party_i.key`) or uses SSL contexts configured in code or ini files.

### 1.7 Security Model & MPyC Guarantees
- **Adversary Model**: **Passive (Honest-but-Curious)**.
- **Honest Majority Requirement**: Requires $m > 2t$. For $m=3$, requires $t=1$.
  - At least $2$ out of $3$ parties must be honest.
  - If at most $1$ party is passively corrupted, **information-theoretic secrecy** is guaranteed.
- **Active / Malicious Corruptions**: MPyC does **not** provide Byzantine fault tolerance or malicious security with abort for generic arithmetic out-of-the-box. An active adversary can send incorrect shares to skew the output.

---

## 2. Mathematical Foundations & Formal Proof

### 2.1 The Polynomial Construction
Let $\mathbb{F}_p$ be a finite field defined modulo a prime $p$.
A secret $s \in \mathbb{F}_p$ is shared among $m = 3$ parties with threshold $t = 1$.
The dealer chooses a random coefficient $a \xleftarrow{\$} \mathbb{F}_p$ and defines the polynomial:
$$f(x) = s + a \cdot x \pmod p$$
- Constant term: $f(0) = s$ (the secret).
- Degree: $\deg(f) = 1$.
- Evaluation points: Distinct non-zero elements $x_0 = 1, x_1 = 2, x_2 = 3$.
- Share for party $j$:
  $$[s]_j = f(x_j) = s + a \cdot x_j \pmod p$$

### 2.2 Lagrange Basis Polynomials
Given $k = t+1 = 2$ shares $(x_u, y_u)$ and $(x_v, y_v)$, the polynomial $f(x)$ is uniquely reconstructed via Lagrange interpolation:
$$f(x) = y_u \cdot \ell_u(x) + y_v \cdot \ell_v(x) \pmod p$$
Where the Lagrange basis polynomials are:
$$\ell_u(x) = \frac{x - x_v}{x_u - x_v} \pmod p, \quad \ell_v(x) = \frac{x - x_u}{x_v - x_u} \pmod p$$
To recover the secret $s = f(0)$:
$$\ell_u(0) = \frac{-x_v}{x_u - x_v} = \frac{x_v}{x_v - x_u} \pmod p$$
$$\ell_v(0) = \frac{-x_u}{x_v - x_u} = \frac{x_u}{x_u - x_v} \pmod p$$
$$s = f(0) = y_u \cdot \ell_u(0) + y_v \cdot \ell_v(0) \pmod p$$

### 2.3 Linear Homomorphism of Secure Summation
Let three founders have secrets $s_0, s_1, s_2 \in \mathbb{F}_p$.
Each founder $i$ samples $a_i \xleftarrow{\$} \mathbb{F}_p$ and forms:
$$f_i(x) = s_i + a_i \cdot x \pmod p$$
Party $j$ receives $[s_i]_j = f_i(x_j)$ for each $i \in \{0, 1, 2\}$.
Party $j$ computes:
$$[S]_j = \sum_{i=0}^{2} [s_i]_j = \sum_{i=0}^2 f_i(x_j) \pmod p$$
Define the aggregate polynomial:
$$F(x) = \sum_{i=0}^{2} f_i(x) = \left(\sum_{i=0}^2 s_i\right) + \left(\sum_{i=0}^2 a_i\right) x = S + A \cdot x \pmod p$$
Notice:
1. $F(0) = S = s_0 + s_1 + s_2$.
2. $\deg(F) \le 1$.
3. $[S]_j = F(x_j)$.
Therefore, the local sum of shares is an exact, valid Shamir share of the total sum $S$ under polynomial $F(x)$.

---

## 3. Concrete Numerical Example

### 3.1 Setup with Illustrative Prime $p = 31$
- Prime Field: $\mathbb{F}_{31}$ ($p = 31$).
- Parties: $m = 3$ with evaluation points $x_0 = 1, x_1 = 2, x_2 = 3$.
- Threshold: $t = 1$ (reconstruction requires $t+1 = 2$ shares).

#### Founder Inputs:
- Founder 0 Salary: $s_0 = 5$
- Founder 1 Salary: $s_1 = 8$
- Founder 2 Salary: $s_2 = 11$
- Expected Sum: $S = 5 + 8 + 11 = 24$
- Expected Average: $\text{Avg} = 24 / 3 = 8$

### 3.2 Share Generation
1. **Founder 0** selects random coefficient $a_0 = 7$:
   $$f_0(x) = 5 + 7x \pmod{31}$$
   - Party 0 ($x=1$): $[s_0]_0 = 5 + 7(1) = 12 \pmod{31}$
   - Party 1 ($x=2$): $[s_0]_1 = 5 + 7(2) = 19 \pmod{31}$
   - Party 2 ($x=3$): $[s_0]_2 = 5 + 7(3) = 26 \pmod{31}$

2. **Founder 1** selects random coefficient $a_1 = 11$:
   $$f_1(x) = 8 + 11x \pmod{31}$$
   - Party 0 ($x=1$): $[s_1]_0 = 8 + 11(1) = 19 \pmod{31}$
   - Party 1 ($x=2$): $[s_1]_1 = 8 + 11(2) = 30 \pmod{31}$
   - Party 2 ($x=3$): $[s_1]_2 = 8 + 11(3) = 41 \equiv 10 \pmod{31}$

3. **Founder 2** selects random coefficient $a_2 = 4$:
   $$f_2(x) = 11 + 4x \pmod{31}$$
   - Party 0 ($x=1$): $[s_2]_0 = 11 + 4(1) = 15 \pmod{31}$
   - Party 1 ($x=2$): $[s_2]_1 = 11 + 4(2) = 19 \pmod{31}$
   - Party 2 ($x=3$): $[s_2]_2 = 11 + 4(3) = 23 \pmod{31}$

### 3.3 Local Secure Summation
Each party computes their local sum share $[S]_j$:
- **Party 0** ($x=1$):
  $$[S]_0 = [s_0]_0 + [s_1]_0 + [s_2]_0 = 12 + 19 + 15 = 46 \equiv 15 \pmod{31}$$
- **Party 1** ($x=2$):
  $$[S]_1 = [s_0]_1 + [s_1]_1 + [s_2]_1 = 19 + 30 + 19 = 68 \equiv 6 \pmod{31}$$
- **Party 2** ($x=3$):
  $$[S]_2 = [s_0]_2 + [s_1]_2 + [s_2]_2 = 26 + 10 + 23 = 59 \equiv 28 \pmod{31}$$

### 3.4 Lagrange Reconstruction Verification
Let any two parties combine their shares:

#### Case A: Using Party 0 ($x_0=1, y_0=15$) and Party 1 ($x_1=2, y_1=6$)
$$\ell_0(0) = \frac{x_1}{x_1 - x_0} = \frac{2}{2 - 1} = 2 \pmod{31}$$
$$\ell_1(0) = \frac{x_0}{x_0 - x_1} = \frac{1}{1 - 2} = -1 \equiv 30 \pmod{31}$$
$$S = y_0 \cdot \ell_0(0) + y_1 \cdot \ell_1(0) = 15(2) + 6(-1) = 30 - 6 = 24 \pmod{31}$$
$$\text{Average} = \frac{24}{3} = 8 \quad \checkmark$$

#### Case B: Using Party 1 ($x_1=2, y_1=6$) and Party 2 ($x_2=3, y_2=28$)
$$\ell_1(0) = \frac{x_2}{x_2 - x_1} = \frac{3}{3 - 2} = 3 \pmod{31}$$
$$\ell_2(0) = \frac{x_1}{x_1 - x_2} = \frac{2}{2 - 3} = -2 \equiv 29 \pmod{31}$$
$$S = 6(3) + 28(-2) = 18 - 56 = -38 \equiv 24 \pmod{31}$$
$$\text{Average} = \frac{24}{3} = 8 \quad \checkmark$$

### 3.5 Demonstration vs. Production Parameters

| Parameter / Aspect | Demonstration Setup ($p = 31$) | Production Cryptographic Setup |
| :--- | :--- | :--- |
| **Field Size $p$** | $p = 31$ (5 bits) | 61-bit Mersenne prime ($2^{61}-1$) or 128-bit/256-bit prime |
| **Overflow Capacity** | Sum must not exceed 30 ($\sum s_i < 31$) | Supports salaries up to millions (\$10M+) without modular wrap ($\sum s_i \ll p$) |
| **Entropy / Brute Force** | Brute force guessing probability: $1/31 \approx 3.2\%$ | Brute force probability: $2^{-61} \approx 4.3 \times 10^{-19}$ (statistically negligible) |
| **Floating/Fixed-Point** | Pure integer arithmetic | Fixed-point fractional precision via `SecFxp` or integer arithmetic with scaling factor |
| **Randomness Source** | Hardcoded toy values | Cryptographically secure CSPRNG (`os.urandom` / `secrets`) |

---

## 4. Exact MPyC APIs & Protocol Mapping

| Capability | MPyC API / Command | Description |
| :--- | :--- | :--- |
| **Runtime Initialization** | `from mpyc.runtime import mpc`<br>`await mpc.start()` | Boots the asynchronous networking engine and connects to peers. |
| **Runtime Shutdown** | `await mpc.stop()` | Gracefully disconnects all party sockets. |
| **Secure Integer Type** | `secint = mpc.SecInt(l=32)` | Defines 32-bit secure integer type over prime field $\mathbb{F}_p$. |
| **Secure Input Distribution**| `shares = mpc.input(secint(val))` | Distributes Shamir shares peer-to-peer. |
| **Homomorphic Sum** | `total = sum(shares)` | Local addition of `SecInt` objects without network communication. |
| **Reconstruction** | `clear_sum = await mpc.output(total)` | Lagrange reconstruction across parties. |
| **CLI Execution** | `python protocol.py -M3 -I{pid} -T1` | Runs party `pid` with 3 total nodes and threshold 1. |
| **Encrypted Transport** | `--ssl` flag | Enables TLS on inter-node TCP sockets. |

---

## 5. Implementation Decisions & Security Limitations

1. **Passive vs Malicious Demarcation**:
   - MPyC natively protects against **honest-but-curious** parties under the $t=1, m=3$ honest majority assumption.
   - We will **not** claim Byzantine fault tolerance or malicious defense against share falsification, because standard MPyC Shamir sharing does not incorporate message authentication codes (MACs).
2. **2-Party Collusion Boundary**:
   - Because $t=1$, two colluding parties can pool shares to solve the degree-1 polynomial and recover any founder's private input. This is a fundamental mathematical property of $(1, 3)$-threshold schemes and will be clearly communicated.
3. **Data Minimization Guarantee**:
   - The coordinator backend only handles session routing and will never inspect or persist shares.
   - Individual founder inputs are passed exclusively to their designated party node.
