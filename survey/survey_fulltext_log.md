# Survey full-text log (B-2 / B-3)

Every row below corresponds to a full text that was actually opened and searched. `url_checked` is the URL used; `check_date` is 2026-10-12/13.

## Screening closure

| stage | n | note |
|---|---|---|
| N0 records identified from all queries | 1136 | Semantic Scholar + arXiv + OpenAlex, 2017-2026 |
| N1 after de-duplication | 1082 | key = DOI -> arXiv id -> norm(title)+first-author surname+year |
| N2 advanced to full-text retrieval (tier T1+T2) | 139 | T1=57 (explicit rounds-to-target wording), T2=82 (threshold + rounds), T3=152 (rounds or accuracy only), T0=845 (unrelated) |
| full texts obtained and adjudicated | 238 | includes 2 duplicate local copies |
| N3 = main pool | 58 | I1-I5 satisfied, E1-E6 clear |
| secondary pool | 15 | E3(b)(c)(d)(f) neighbouring constructions, registered but not counted |

Exclusions by primary reason (one code per record):

| code | n |
|---|---|
| E2 | 118 |
| E3 | 9 |
| E3(b) | 1 |
| E3(c) | 14 |
| E3(d) | 15 |
| E4 | 1 |
| E6 | 5 |
| E-duplicate | 2 |

## Per-record log

| study_id | file | title | year | verdict | reason/code | target | url_checked |
|---|---|---|---|---|---|---|---|
| S001 |  | Federated Multi-Mini-Batch: An Efficient Training Approach t | 2020 | main | - | 0.70 | https://arxiv.org/abs/2011.07006 |
| S002 |  | Clustered Scheduling and Communication Pipelining for Effici | 2023 | main | - | 0.96 | https://arxiv.org/abs/2206.07631 |
| S003 |  | Digital Twin-Driven Communication-Efficient Federated Anomal | 2026 | main | - | 0.80 | https://arxiv.org/abs/2601.01701 |
| S004 |  | VARS-FL: Validation-Aligned Client Selection for Non-IID Fed | 2026 | main | - | 0.80 | https://arxiv.org/pdf/2605.05896 |
| S005 |  | FedADMM: A Robust Federated Deep Learning Framework with Ada | 2022 | main | - | 0.97 | https://arxiv.org/abs/2204.03529 |
| S006 |  | GTFLAT: Game Theory Based Add-On For Empowering Federated Le | 2022 | main | - | 0.50 | https://arxiv.org/pdf/2212.04103 |
| S007 |  | Flashback: Understanding and Mitigating Forgetting in Federa | 2025 | main | - | 0.80 | https://arxiv.org/pdf/2402.05558 |
| S008 |  | NTK-DFL: Enhancing Decentralized Federated Learning in Heter | 2024 | main | - | 0.85 | https://arxiv.org/abs/2410.01922 |
| S009 |  | Communication-Efficient Neural Tangent Kernels for Heterogen | 2025 | main | - | 0.85 | https://arxiv.org/abs/2512.12737 |
| S010 |  | Distributionally Robust Federated Learning With Client Drift | 2026 | main | - | 0.85 | https://doi.org/10.1109/tmlcn.2026.3658026 |
| S011 |  | FedSA: Accelerating Intrusion Detection in Collaborative Env | 2022 | main | - | 0.97 | https://arxiv.org/pdf/2205.11519 |
| S012 |  | Federated Learning for Keyword Spotting | 2018 | main | - | 0.95 | https://arxiv.org/abs/1810.05512 |
| S013 |  | Adaptive Privacy Budget Allocation for Differential Privacy  | 2026 | main | - | 0.80 | https://scipublication.com/index.php/AIMLR/article/download/275/252 |
| S014 |  | Federated Learning for Malicious Domain Detection via Privac | 2026 | main | - | 0.9998 | https://cdn.techscience.press/files/cmc/2026/TSP_CMC-87-3/TSP_CMC_77337/TSP_CMC_77337.pdf |
| S015 |  | Multi-Task Federated Learning for Personalised Deep Neural N | 2020 | secondary | - | unspecified | https://arxiv.org/html/2007.09236v1 |
| S016 |  | FedDCT: Federated Learning of Large Convolutional Neural Net | 2022 | main | - | 0.80 | https://arxiv.org/abs/2211.10948 |
| S017 |  | FAGH: Accelerating Federated Learning with Approximated Glob | 2024 | main | - | 0.60 | https://arxiv.org/abs/2403.11041 |
| S018 |  | LEFL: Low Entropy Client Sampling in Federated Learning | 2023 | main | - | 0.70 | https://arxiv.org/abs/2312.17430 |
| S019 |  | Power-Efficient Over-the-Air Aggregation With Receive Beamfo | 2025 | main | - | 0.70 | https://arxiv.org/abs/2501.18058 |
| S020 |  | Energy Efficient Federated Learning with Hyperdimensional Co | 2026 | main | - | 0.90 | https://arxiv.org/abs/2602.21949 |
| S021 |  | Communication-Efficient Federated Learning under Non-IID Dat | 2026 | main | - | 0.95 | https://ace.ewapub.com/article/view/37334.pdf |
| S022 |  | Robust and Communication-Efficient Federated Learning from N | 2019 | secondary | - | unspecified | https://arxiv.org/pdf/1903.02891 |
| S023 |  | SA-PEF: Step-Ahead Partial Error Feedback for Efficient Fede | 2026 | secondary | - | unspecified | https://arxiv.org/abs/2601.20738 |
| S024 |  | Green, Quantized Federated Learning over Wireless Networks:  | 2022 | secondary | - | unspecified | https://arxiv.org/abs/2207.09387 |
| S025 |  | Hidden in Rounds: Predicting the Time Cost of 802.11 Content | 2026 | secondary | - | unspecified | https://arxiv.org/abs/2609.12903 |
| S026 |  | Speeding up Heterogeneous Federated Learning with Sequential | 2022 | main | - | 0.70 | https://arxiv.org/abs/2201.10899 |
| S027 |  | Fed-BAC: Federated Bandit-Guided Additive Clustering in Hier | 2026 | main | - | 0.80 | https://arxiv.org/abs/2605.11815 |
| S028 |  | FedEff: efficient federated learning with optimal local epoc | 2025 | main | - | 0.92 | https://www.nature.com/articles/s41598-025-22672-1.pdf |
| S029 |  | A federated learning framework for Non-IID data : data featu | 2026 | main | - | 0.89 | https://www.nature.com/articles/s41598-026-74398-3_reference.pdf |
| S030 |  | Achieving consistency in FedSAM using local adaptive distill | 2025 | main | - | 0.60 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0333210&type=printable |
| S031 |  | Beyond Fixed Rounds: Data-Free Early Stopping for Practical  | 2026 | secondary | - | unspecified | https://arxiv.org/pdf/2601.22669 |
| S032 |  | Dataset-centric evaluation of federated intrusion detection  | 2026 | main | - | 0.95 | https://www.nature.com/articles/s41598-025-32567-w_reference.pdf |
| S033 |  | Federated Learning with Additional Mechanisms on Clients to  | 2019 | main | - | 0.94 | https://arxiv.org/html/1908.05891v2 |
| S034 |  | Fast-Convergent Federated Learning | 2020 | main | - | 0.80 | https://arxiv.org/html/2007.13137v2 |
| S035 |  | Fast-Convergent Federated Learning with Adaptive Weighting | 2020 | main | - | 0.95 | https://arxiv.org/html/2012.00661v2 |
| S036 |  | Contextual Model Aggregation for Fast and Robust Federated L | 2022 | main | - | 0.50 | https://arxiv.org/html/2203.12738v1 |
| S037 |  | Time-Triggered Federated Learning Over Wireless Networks | 2022 | main | - | 0.80 | https://arxiv.org/html/2204.12426v2 |
| S038 |  | FedEntropy: Efficient Device Grouping for Federated Learning | 2022 | main | - | 0.30 | https://arxiv.org/html/2205.12038v1 |
| S039 |  | Enhancing Heterogeneous Federated Learning with Knowledge Ex | 2023 | main | - | 0.60 | https://arxiv.org/html/2208.07978v2 |
| S040 |  | On-Demand-FL: A Dynamic and Efficient Multicriteria Federate | 2023 | main | - | 0.60 | https://arxiv.org/html/2211.02906v1 |
| S041 |  | Communication-Efficient Federated Learning for Heterogeneous | 2023 | main | - | 0.85 | https://arxiv.org/html/2212.08272v1 |
| S042 |  | FedAVO: Improving Communication Efficiency in Federated Lear | 2024 | main | - | 0.90 | https://arxiv.org/html/2305.01154v3 |
| S043 |  | An Efficient Virtual Data Generation Method for Reducing Com | 2023 | main | - | 0.55 | https://arxiv.org/html/2306.12088v3 |
| S044 |  | FLASH-RL: Federated Learning Addressing System and Static He | 2023 | main | - | 0.95 | https://arxiv.org/html/2311.06917v1 |
| S045 |  | Communication-Efficient Federated Optimization over Semi-Dec | 2023 | main | - | 0.80 | https://arxiv.org/html/2311.18787v4 |
| S046 |  | FedClust: Tackling Data Heterogeneity in Federated Learning  | 2024 | main | - | 0.70 | https://arxiv.org/html/2407.07124v1 |
| S047 |  | Exploiting Adaptive Channel Pruning for Communication-Effici | 2026 | main | - | 0.65 | https://arxiv.org/html/2603.09792v2 |
| S048 |  | Optimizing the Communication-Accuracy Trade-off in Federated | 2022 | secondary | - | unspecified | https://arxiv.org/html/2201.02664v3 |
| S049 |  | EPISODE: Episodic Gradient Clipping with Periodic Resampled  | 2023 | secondary | - | 0.40 | https://arxiv.org/html/2302.07155v1 |
| S050 |  | Optimal Batch-Size Control for Low-Latency Federated Learnin | 2025 | secondary | - | unspecified | https://arxiv.org/abs/2507.15601 |
| S051 |  | Federated Learning with Unbiased Gradient Aggregation and Co | 2019 | main | - | 0.75 | https://arxiv.org/html/1910.08234v3 |
| S052 |  | Federated Generalized Bayesian Learning via Distributed Stei | 2020 | main | - | 0.70 | https://arxiv.org/html/2009.06419v6 |
| S053 |  | FedProf: Selective Federated Learning with Representation Pr | 2021 | main | - | 0.90 | https://arxiv.org/html/2102.01733v9 |
| S054 |  | Precision‐Weighted Federated Learning | 2025 | main | - | 0.75 | https://arxiv.org/html/2107.09627v1 |
| S055 |  | Neural Tangent Kernel Empowered Federated Learning | 2021 | main | - | 0.85 | https://arxiv.org/html/2110.03681v3 |
| S056 |  | Federated Semi-Supervised Learning with Class Distribution M | 2021 | main | - | 0.76 | https://arxiv.org/html/2111.00010v1 |
| S057 |  | Heterogeneous Federated Learning via Grouped Sequential-to-P | 2022 | main | - | 0.80 | https://arxiv.org/html/2201.12976v1 |
| S058 |  | Efficient Federated Learning on Knowledge Graphs via Privacy | 2022 | main | - | 0.40 | https://arxiv.org/html/2203.09553v3 |
| S059 |  | UNIDEAL: Curriculum Knowledge Distillation Federated Learnin | 2024 | main | - | 0.50 | https://arxiv.org/html/2309.08961v1 |
| S060 |  | Mobility Accelerates Learning: Convergence Analysis on Hiera | 2025 | main | - | 0.75 | https://arxiv.org/html/2401.09656v1 |
| S061 |  | Federated Learning in Mobile Edge Networks: A Comprehensive  | 2019 | main | - | 0.80 | https://arxiv.org/html/1909.11875v2 |
| S062 |  | Improving Federated Learning Personalization via Model Agnos | 2019 | main | - | 0.80 | https://arxiv.org/html/1909.12488v2 |
| S063 |  | From Deterioration to Acceleration: A Calibration Approach t | 2023 | main | - | 0.80 | https://arxiv.org/html/2112.09355v2 |
| S064 |  | Deep Reinforcement Learning Assisted Federated Learning Algo | 2022 | main | - | 0.98 | https://arxiv.org/html/2202.03575v1 |
| S065 |  | Fine-tuning Global Model via Data-Free Knowledge Distillatio | 2022 | main | - | 0.75 | https://arxiv.org/html/2203.09249v2 |
| S066 |  | FedDC: Federated Learning with Non-IID Data via Local Drift  | 2022 | main | - | 0.40 | https://arxiv.org/html/2203.11751v1 |
| S067 |  | ADDS: Adaptive Differentiable Sampling for Robust Multi-Part | 2021 | main | - | 0.50 | https://arxiv.org/html/2110.15522v1 |
| S068 |  | Oort: Efficient Federated Learning via Guided Participant Se | 2020 | secondary | - | 0.531 | https://arxiv.org/html/2010.06081v3 |
| S069 |  | Rethinking Architecture Design for Tackling Data Heterogenei | 2021 | secondary | - | unspecified | https://arxiv.org/html/2106.06047v2 |
| S070 |  | Is Shapley Value fair? Improving Client Selection for Maveri | 2021 | secondary | - | unspecified | https://arxiv.org/html/2106.10734v1 |
| S071 |  | Federated Distributionally Robust Optimization for Phase Con | 2021 | secondary | - | unspecified | https://arxiv.org/html/2108.09026v2 |
| S072 |  | Achieving Personalized Federated Learning with Sparse Local  | 2022 | secondary | - | unspecified | https://arxiv.org/html/2201.11380v1 |
| S073 |  | Tackling System and Statistical Heterogeneity for Federated  | 2022 | secondary | - | unspecified | https://arxiv.org/html/2112.11256v1 |
| - | 2004.11791 | Federated learning with hierarchical clustering of local upd | 2020 | exclude | E3 | - | https://arxiv.org/pdf/2004.11791 |
| - | 2402.10097 | Adaptive Federated Learning in Heterogeneous Wireless Networ | 2024 | exclude | E3(c) | - | https://arxiv.org/abs/2402.10097 |
| - | 2003.00229 | User-Level Privacy-Preserving Federated Learning: Analysis a | 2020 | exclude | E3(c) | - | https://arxiv.org/pdf/2003.00229 |
| - | 2303.08423 | Communication-Efficient Design for Quantized Decentralized F | 2024 | exclude | E3(c) | - | https://arxiv.org/pdf/2303.08423 |
| - | 2505.07629 | Enhancing Federated Learning with Kolmogorov-Arnold Networks | 2025 | exclude | E2 | - | https://arxiv.org/abs/2505.07629 |
| - | 2603.04422 | FedEMA-Distill: Exponential Moving Average Guided Knowledge  | 2026 | exclude | E2 | - | https://arxiv.org/abs/2603.04422 |
| - | 2506.07159 | pFedSOP : Accelerating Training Of Personalized Federated Le | 2025 | exclude | E2 | - | https://arxiv.org/abs/2506.07159 |
| - | 2404.10110 | Communication-Efficient Hybrid Federated Learning for E-Heal | 2024 | exclude | E2 | - | https://arxiv.org/abs/2404.10110 |
| - | 2607.06979 | Robust Federated Learning Under Real-World Client Churn | 2026 | exclude | E3 | - | https://arxiv.org/abs/2607.06979 |
| - | 2601.10491 | Communication-Efficient Federated Learning by Exploiting Spa | 2026 | exclude | E3 | - | https://arxiv.org/abs/2601.10491 |
| - | 2008.01558 | Federated Learning with Sparsification-Amplified Privacy and | 2020 | exclude | E3 | - | https://www.ijcai.org/proceedings/2021/0202.pdf |
| - | 10.1007_s00607-026-01685-2 | Fast-converging federated decision trees for smart-home ener | 2026 | exclude | E3 | - | https://link.springer.com/content/pdf/10.1007/s00607-026-01685-2.pdf |
| - | 2507.21901 | Communication-Efficient Decentralized Stochastic Minimax Opt | 2025 | exclude | E6 | - | https://arxiv.org/abs/2507.21901 |
| - | 2606.07496 | Accelerated Decentralized Stochastic Gradient Descent for St | 2026 | exclude | E6 | - | https://arxiv.org/abs/2606.07496 |
| - | 2312.11861 | A Proximal Gradient Method With Probabilistic Multi-Gossip C | 2023 | exclude | E6 | - | https://arxiv.org/abs/2312.11861 |
| - | 1811.01903 | Lower Bounds for Parallel and Randomized Convex Optimization | 2018 | exclude | E6 | - | https://arxiv.org/abs/1811.01903 |
| - | 2607.22002 | Learning as Reasoning Unfolds: Progressive Rollout Allocatio | 2026 | exclude | E6 | - | https://arxiv.org/abs/2607.22002 |
| - | 2606.10595 | From data heterogeneity to convergence: A data-centric revie | 2026 | exclude | E4 | - | https://arxiv.org/abs/2606.10595 |
| - | 2205.11440 | Federated Distillation Based Indoor Localization for IoT Net | 2022 | exclude | E2 | - | https://arxiv.org/abs/2205.11440 |
| - | 2208.12911 | Network-Level Adversaries in Federated Learning | 2022 | exclude | E2 | - | https://arxiv.org/abs/2208.12911 |
| - | 2508.06692 | HeteRo-Select: Informativeness as the Participation Driver i | 2025 | exclude | E2 | - | https://arxiv.org/abs/2508.06692 |
| - | 2011.09849 | Budgeted Online Selection of Candidate IoT Clients to Partic | 2020 | exclude | E2 | - | https://arxiv.org/abs/2011.09849 |
| - | 2410.05662 | Communication-Efficient Federated Learning under Dynamic Dev | 2024 | exclude | E2 | - | https://arxiv.org/abs/2410.05662 |
| - | 2607.20641 | One Round Is All You Need: Analytic Federated Learning for T | 2026 | exclude | E2 | - | https://arxiv.org/abs/2607.20641 |
| - | 1912.11187 | A Communication Efficient Collaborative Learning Framework f | 2019 | exclude | E3 | - | https://arxiv.org/pdf/1912.11187 |
| - | 2503.10961 | FedOSAA: Improving Federated Learning with One-Step Anderson | 2025 | exclude | E3 | - | https://arxiv.org/abs/2503.10961 |
| - | 10.3934_math.2023769 | A novel Bayesian federated learning framework to address mul | 2023 | exclude | E2 | - | http://www.aimspress.com/aimspress-data/math/2023/7/PDF/math-08-07-769.pdf |
| - | 10.1109_access.2024.3387453 | Accelerating Federated Learning via Sequential Training of G | 2024 | exclude | E2 | - | https://ieeexplore.ieee.org/ielx7/6287639/6514899/10497106.pdf |
| - | 10.55529_jaimlnn.52.69.78 | Privacy-preserving federated learning with differential priv | 2025 | exclude | E2 | - | https://journal.hmjournals.com/index.php/JAIMLNN/article/download/6340/4029 |
| - | 10.54254_2755-2721_2026.34419 | Fairness-Aware Client Scheduling Strategy for Federated Lear | 2026 | exclude | E2 | - | https://ace.ewapub.com/article/view/34419.pdf |
| - | 10.54254_2755-2721_2026.33840 | Quantitative Analysis of the Impact of Data Heterogeneity on | 2026 | exclude | E2 | - | https://ace.ewapub.com/article/view/33840.pdf |
| - | OptimizationofFederatedLear | Optimization of Federated Learning in Edge Computing Using A | 2025 | exclude | E3 | - | https://iocscience.org/ejournal/index.php/JBST/article/download/7455/4713 |
| - | 2508.08552 | SHEFL: Sparse Heterogeneous Ensemble Federated Learning with | 2025 | exclude | E3 | - | https://arxiv.org/pdf/2508.08552 |
| - | 10.56726_irjmets98517 | Federated Learning for Human Activity Recognition: Accuracy, | 2026 | exclude | E2 | - | https://doi.org/10.56726/irjmets98517 |
| - | 10.33889_ijmems.2026.11.3.052 | SAB-Select Staleness-Aware Burst-Adaptive Client Selection f | 2026 | exclude | E2 | - | https://doi.org/10.33889/ijmems.2026.11.3.052 |
| - | 10.34028_iajit_22_6_1 | Strategic optimization of convergence and energy in federate | 2025 | exclude | E2 | - | https://doi.org/10.34028/iajit/22/6/1 |
| - | 10.1109_globecom48099.2022.10000898 | Communication-Efficient Federated Learning in Channel Constr | 2022 | exclude | E2 | - | https://jyx.jyu.fi/bitstreams/8901953a-5e07-4e97-9914-7e4f15bfcb03/download |
| - | 10.14569_ijacsa.2026.0170891 | A Heterogeneity-Aware Federated Learning Framework for Graph | 2026 | exclude | E2 | - | https://doi.org/10.14569/ijacsa.2026.0170891 |
| - | _t2 | _t2 | unspecified | exclude | E-duplicate | - | unspecified |
| - | t | TCFL: Trapdoor homomorphic encryption based federated learni | 2026 | exclude | E-duplicate | - | https://link.springer.com/content/pdf/10.1007/s12083-025-02193-4.pdf |
| - | 10.1007_s11036-026-02530-8 | Adaptive and Fault-Tolerant Scheduling Framework for Scalabl | 2026 | exclude | E2 | - | https://link.springer.com/content/pdf/10.1007/s11036-026-02530-8.pdf |
| - | 10.1038_s41598-026-41093-2 | Personalized multi-agent reinforcement learning framework fo | 2026 | exclude | E2 | - | https://www.nature.com/articles/s41598-026-41093-2_reference.pdf |
| - | 10.3389_fdgth.2026.1856286 | Fed-XLM-R: a privacy-preserving federated framework with ada | 2026 | exclude | E2 | - | https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2026.1856286/pdf |
| - | 10.52436_1.jutif.2026.7.4.6012 | Particle Swarm Optimization for Hyperparameter Tuning in Fed | 2026 | exclude | E2 | - | https://jutif.if.unsoed.ac.id/index.php/jurnal/article/download/6012/1376 |
| - | 10.1109_satml64287.2025.00045 | Fair Decentralized Learning | 2025 | exclude | E3(d) | - | https://arxiv.org/pdf/2410.02541 |
| - | 10.48550_arxiv.2412.19989 | Caesar: A Low-deviation Compression Approach for Efficient F | 2024 | exclude | E3(d) | - | https://arxiv.org/pdf/2412.19989 |
| - | 10.48550_arxiv.2307.15870 | SemiSFL: Split Federated Learning on Unlabeled and Non-IID D | 2023 | exclude | E3(d) | - | https://arxiv.org/pdf/2307.15870 |
| - | 10.48550_arxiv.2511.11949 | Computation-aware Energy-harvesting Federated Learning with  | 2025 | exclude | E3(d) | - | https://arxiv.org/pdf/2511.11949 |
| - | 10.48550_arxiv.2305.00504 | Green Federated Learning Over Cloud-RAN with Limited Fronthu | 2023 | exclude | E3(d) | - | https://arxiv.org/pdf/2305.00504 |
| - | 10.63125_4k4pjr64 | Federated Learning Architectures for Distributed Engineering | 2022 | exclude | E3(b) | - | https://rast-journal.org/index.php/RAST/article/download/125/124 |
| - | 1805.09965 | LAG: Lazily Aggregated Gradient for Communication-Efficient  | 2018 | exclude | E2 | - | https://arxiv.org/html/1805.09965v2 |
| - | 1910.13067 | Federated Learning Over Wireless Networks: Convergence Analy | 2019 | exclude | E3(c) | - | https://arxiv.org/html/1910.13067v4 |
| - | 1910.14425 | On the Convergence of Local Descent Methods in Federated Lea | 2019 | exclude | E3(c) | - | https://arxiv.org/html/1910.14425v2 |
| - | 1912.00513 | A Quasi-Newton Method Based Vertical Federated Learning Fram | 2019 | exclude | E2 | - | https://arxiv.org/html/1912.00513v2 |
| - | 2002.08196 | Federated Learning in the Sky: Joint Power Allocation and Sc | 2020 | exclude | E3(c) | - | https://arxiv.org/abs/2002.08196 |
| - | 2002.08958 | Uncertainty Principle for Communication Compression in Distr | 2020 | exclude | E2 | - | https://arxiv.org/html/2002.08958v3 |
| - | 2003.01575 | Evaluation Framework For Large-scale Federated Learning | 2020 | exclude | E2 | - | https://arxiv.org/html/2003.01575v2 |
| - | 2007.07174 | Joint Device Scheduling and Resource Allocation for Latency  | 2020 | exclude | E3(d) | - | https://arxiv.org/html/2007.07174v1 |
| - | 2009.02031 | Joint Resource Allocation to Minimize Execution Time of Fede | 2020 | exclude | E2 | - | https://arxiv.org/abs/2009.02031 |
| - | 2009.07999 | Distilled One-Shot Federated Learning | 2020 | exclude | E2 | - | https://arxiv.org/abs/2009.07999 |
| - | 2102.01593 | FEDZIP: A Compression Framework for Communication-Efficient  | 2021 | exclude | E2 | - | https://arxiv.org/html/2102.01593v1 |
| - | 2104.12749 | Simultaneous Wireless Information and Power Transfer for Fed | 2021 | exclude | E2 | - | https://arxiv.org/html/2104.12749v2 |
| - | 2107.09461 | CANITA: Faster Rates for Distributed Convex Optimization wit | 2021 | exclude | E2 | - | https://arxiv.org/html/2107.09461v2 |
| - | 2108.04755 | FedPAGE: A Fast Local Stochastic Gradient Method for Communi | 2021 | exclude | E2 | - | https://arxiv.org/html/2108.04755v1 |
| - | 2108.06869 | FedChain: Chained Algorithms for Near-Optimal Communication  | 2021 | exclude | E2 | - | https://arxiv.org/html/2108.06869v5 |
| - | 2109.08344 | Achieving Model Fairness in Vertical Federated Learning | 2021 | exclude | E2 | - | https://arxiv.org/html/2109.08344v3 |
| - | 2109.12519 | AsySQN: Faster Vertical Federated Learning Algorithms with B | 2021 | exclude | E2 | - | https://arxiv.org/html/2109.12519v1 |
| - | 2110.12292 | Federated Multiple Label Hashing (FedMLH): Communication Eff | 2021 | exclude | E2 | - | https://arxiv.org/html/2110.12292v1 |
| - | 2111.04105 | DQRE-SCnet: A novel hybrid approach for selecting users in F | 2021 | exclude | E2 | - | https://arxiv.org/abs/2111.04105 |
| - | 2111.14345 | SPATL: Salient Parameter Aggregation and Transfer Learning f | 2021 | exclude | E2 | - | https://arxiv.org/html/2111.14345v2 |
| - | 2111.14789 | Dynamic Network-Assisted D2D-Aided Coded Distributed Learnin | 2021 | exclude | E2 | - | https://arxiv.org/html/2111.14789v2 |
| - | 2112.13097 | Faster Rates for Compressed Federated Learning with Client-V | 2021 | exclude | E2 | - | https://arxiv.org/html/2112.13097v3 |
| - | 2112.14387 | Training Time Minimization for Federated Edge Learning with  | 2021 | exclude | E3(c) | - | https://arxiv.org/html/2112.14387v2 |
| - | 2202.05800 | SHED: A Newton-type algorithm for federated learning based o | 2022 | exclude | E2 | - | https://arxiv.org/html/2202.05800v2 |
| - | 2203.04376 | Unsupervised Data Splitting Scheme for Federated Edge Learni | 2022 | exclude | E2 | - | https://arxiv.org/html/2203.04376v1 |
| - | 2206.09526 | Robust One Round Federated Learning with Predictive Space Ba | 2022 | exclude | E2 | - | https://arxiv.org/html/2206.09526v1 |
| - | 2207.09653 | FedDM: Iterative Distribution Matching for Communication-Eff | 2022 | exclude | E2 | - | https://arxiv.org/abs/2207.09653 |
| - | 2208.02507 | ZeroFL: Efficient On-Device Training for Federated Learning  | 2022 | exclude | E2 | - | https://arxiv.org/html/2208.02507v1 |
| - | 2209.01417 | Suppressing Noise from Built Environment Datasets to Reduce  | 2022 | exclude | E2 | - | https://arxiv.org/abs/2209.01417 |
| - | 2209.06623 | Convergence Acceleration in Wireless Federated Learning: A S | 2022 | exclude | E2 | - | https://arxiv.org/html/2209.06623v2 |
| - | 2209.14851 | Meta Knowledge Condensation for Federated Learning | 2022 | exclude | E2 | - | https://arxiv.org/html/2209.14851v1 |
| - | 2302.10429 | FedSpeed: Larger Local Interval, Less Communication Round, a | 2023 | exclude | E3(d) | - | https://arxiv.org/html/2302.10429v2 |
| - | 2302.10757 | Distributed Learning in Heterogeneous Environment: Federated | 2023 | exclude | E2 | - | https://arxiv.org/html/2302.10757v1 |
| - | 2305.03547 | Over-the-Air Federated Averaging with Limited Power and Priv | 2023 | exclude | E2 | - | https://arxiv.org/html/2305.03547v1 |
| - | 2305.09628 | Faster Federated Learning With Decaying Number of Local SGD  | 2023 | exclude | E2 | - | https://arxiv.org/html/2305.09628v1 |
| - | 2305.10852 | Q-SHED: Distributed Optimization at the Edge via Hessian Eig | 2023 | exclude | E2 | - | https://arxiv.org/abs/2305.10852 |
| - | 2305.12950 | FSSA: Efficient 3-Round Secure Aggregation for Privacy-Prese | 2023 | exclude | E2 | - | https://arxiv.org/html/2305.12950v1 |
| - | 2305.19442 | SimFBO: Towards Simple, Flexible and Communication-efficient | 2023 | exclude | E3(c) | - | https://arxiv.org/html/2305.19442v5 |
| - | 2306.04207 | Resource Aware Clustering for Tackling the Heterogeneity of  | 2023 | exclude | E2 | - | https://arxiv.org/abs/2306.04207 |
| - | 2306.05862 | Lessons from Generalization Error Analysis of Federated Lear | 2023 | exclude | E2 | - | https://arxiv.org/html/2306.05862v2 |
| - | 2307.13347 | Federated Heavy Hitter Recovery under Linear Sketching | 2023 | exclude | E2 | - | https://arxiv.org/html/2307.13347v1 |
| - | 2310.19059 | Escaping Saddle Points in Heterogeneous Federated Learning v | 2023 | exclude | E3(c) | - | https://arxiv.org/html/2310.19059v1 |
| - | 2312.14309 | Federated Quantum Long Short-term Memory (FedQLSTM) | 2023 | exclude | E2 | - | https://arxiv.org/abs/2312.14309 |
| - | 2312.14567 | Accelerated Convergence of Stochastic Heavy Ball Method unde | 2023 | exclude | E2 | - | https://arxiv.org/html/2312.14567v2 |
| - | 2401.02734 | FedNS: A Fast Sketching Newton-Type Algorithm for Federated  | 2024 | exclude | E2 | - | https://arxiv.org/html/2401.02734v1 |
| - | 2404.13804 | Adaptive Heterogeneous Client Sampling for Federated Learnin | 2024 | exclude | E2 | - | https://arxiv.org/html/2404.13804v1 |
| - | 2404.15611 | Model Poisoning Attacks to Federated Learning via Multi-Roun | 2024 | exclude | E2 | - | https://arxiv.org/html/2404.15611v3 |
| - | 2405.11580 | Securing Health Data on the Blockchain: A Differential Priva | 2024 | exclude | E2 | - | https://arxiv.org/html/2405.11580v1 |
| - | 2405.17932 | Towards Communication-Efficient Federated Learning via Spars | 2025 | exclude | E3(c) | - | https://arxiv.org/html/2405.17932v2 |
| - | 2408.07075 | UniFed: A Universal Federation of a Mixture of Highly Hetero | 2024 | exclude | E2 | - | https://arxiv.org/html/2408.07075v2 |
| - | 2410.23131 | Federated Learning under Periodic Client Participation and H | 2024 | exclude | E2 | - | https://arxiv.org/html/2410.23131v3 |
| - | 2411.06770 | Sketched Adaptive Federated Deep Learning: A Sharp Convergen | 2024 | exclude | E2 | - | https://arxiv.org/html/2411.06770v3 |
| - | 2411.17833 | Adaptive client selection with personalization for communica | 2024 | exclude | E2 | - | https://arxiv.org/html/2411.17833v1 |
| - | 2412.03385 | Reactive Orchestration for Hierarchical Federated Learning U | 2024 | exclude | E2 | - | https://arxiv.org/html/2412.03385v2 |
| - | 2412.14226 | FedSTaS: Client Stratification and Client Level Sampling for | 2024 | exclude | E2 | - | https://arxiv.org/html/2412.14226v2 |
| - | 2502.18706 | Differentially Private Federated Learning With Time-Adaptive | 2025 | exclude | E2 | - | https://arxiv.org/html/2502.18706v1 |
| - | 2502.20565 | Communication-Efficient and Differentially Private Vertical  | 2025 | exclude | E3(d) | - | https://arxiv.org/html/2502.20565v3 |
| - | 2503.04136 | FLAME: A Federated Learning Approach for Multimodal RF Finge | 2025 | exclude | E2 | - | https://arxiv.org/html/2503.04136v2 |
| - | 2505.18494 | FedHL: Federated Learning for Heterogeneous Low-Rank Adaptat | 2025 | exclude | E2 | - | https://arxiv.org/html/2505.18494v1 |
| - | 2505.23182 | FSL-SAGE: Accelerating Federated Split Learning via Smashed  | 2025 | exclude | E2 | - | https://arxiv.org/html/2505.23182v2 |
| - | 2505.23588 | Accelerated Training of Federated Learning via Second-Order  | 2025 | exclude | E2 | - | https://arxiv.org/abs/2505.23588 |
| - | 2505.23973 | Adaptive Deadline and Batch Layered Synchronized Federated L | 2025 | exclude | E2 | - | https://arxiv.org/html/2505.23973v2 |
| - | 2510.02701 | Robust Segmented Analog Broadcast Design to Accelerate Wirel | 2025 | exclude | E2 | - | https://arxiv.org/html/2510.02701v1 |
| - | 2510.27403 | FedMuon: Accelerating Federated Learning with Matrix Orthogo | 2025 | exclude | E2 | - | https://arxiv.org/html/2510.27403v1 |
| - | 2510.27486 | FedAdamW: A Communication-Efficient Optimizer with Convergen | 2025 | exclude | E2 | - | https://arxiv.org/html/2510.27486v3 |
| - | 2511.11208 | When to Stop Federated Learning: Zero-Shot Generation of Syn | 2025 | exclude | E2 | - | https://arxiv.org/html/2511.11208v1 |
| - | 2512.05372 | Breaking the Capacity Bottleneck in Model-Heterogeneous Fede | 2025 | exclude | E2 | - | https://arxiv.org/html/2512.05372v3 |
| - | 2605.18656 | Statistical Limits and Efficient Algorithms for Differential | 2026 | exclude | E2 | - | https://arxiv.org/html/2605.18656v1 |
| - | 2605.30123 | Privacy-Enhanced Zero-Order Federated Learning via xMK-CKKS  | 2026 | exclude | E3(c) | - | https://arxiv.org/html/2605.30123v3 |
| - | 2607.18343 | Federated Lightweight Fine-Tuning | 2026 | exclude | E2 | - | https://arxiv.org/html/2607.18343v1 |
| - | 2608.07730 | FedSceneX: Time-to-Target Orchestration for Same-Scene Multi | 2026 | exclude | E2 | - | https://arxiv.org/html/2608.07730v1 |
| - | 2608.15153 | An Adaptive Gradient Clipping and Noise Injection Mechanism  | 2026 | exclude | E2 | - | https://arxiv.org/html/2608.15153v1 |
| - | 2608.22593 | GCA: Global Centroid Alignment in Federated Learning | 2026 | exclude | E2 | - | https://arxiv.org/html/2608.22593v1 |
| - | 2609.08312 | Non-Coherent Over-the-Air Federated Learning: Protocol, Conv | 2026 | exclude | E2 | - | https://arxiv.org/html/2609.08312v1 |
| - | 2609.14591 | Pathwise Individual Rationality in Federated Learning: A Mec | 2026 | exclude | E2 | - | https://arxiv.org/html/2609.14591v2 |
| - | 2609.36610 | Communication-Efficient Agnostic Federated Learning via Fast | 2026 | exclude | E2 | - | https://arxiv.org/html/2609.36610v1 |
| - | 2610.05915 | Large Stepsizes Federated Learning on Logistic Regression wi | 2026 | exclude | E2 | - | https://arxiv.org/html/2610.05915v1 |
| - | 2201.11036 | Fast Server Learning Rate Tuning for Coded Federated Dropout | 2022 | exclude | E3(d) | - | https://arxiv.org/html/2201.11036v4 |
| - | 2302.14307 | GradMA: A Gradient-Memory-based Accelerated Federated Learni | 2023 | exclude | E3(d) | - | https://arxiv.org/html/2302.14307v3 |
| - | 2308.16835 | FedDD: Toward Communication-Efficient Federated Learning Wit | 2023 | exclude | E3(d) | - | https://arxiv.org/html/2308.16835v2 |
| - | 2006.07242 | Ensemble Distillation for Robust Model Fusion in Federated L | 2020 | exclude | E3(d) | - | https://arxiv.org/html/2006.07242v3 |
| - | 2009.11065 | Edge Learning with Timeliness Constraints: Challenges and So | 2020 | exclude | E3(d) | - | https://arxiv.org/html/2009.11065v1 |
| - | 2012.08336 | Cost-Effective Federated Learning Design | 2021 | exclude | E3(c) | - | https://arxiv.org/html/2012.08336v1 |
| - | 10.4236_oalib.1113954 | Federated Learning for Treatment Response Prediction in Bipo | 2025 | exclude | E2 | - | https://doi.org/10.4236/oalib.1113954 |
| - | 10.5753_jbcs.2024.4325 | A Robust Client Selection Mechanism for Federated Learning E | 2024 | exclude | E2 | - | https://journals-sol.sbc.org.br/index.php/jbcs/article/download/4325/2972 |
| - | 1911.10071 | Federated Learning with Bayesian Differential Privacy | 2019 | exclude | E2 | - | https://arxiv.org/html/1911.10071v1 |
| - | 2009.00471 | Adaptive Path Sampling in Metastable Posterior Distributions | 2020 | exclude | E2 | - | https://arxiv.org/html/2009.00471v1 |
| - | 2010.12229 | Throughput-Optimal Topology Design for Cross-Silo Federated  | 2020 | exclude | E2 | - | https://arxiv.org/html/2010.12229v2 |
| - | 2012.07450 | FedHome: Cloud-Edge Based Personalized Federated Learning fo | 2020 | exclude | E2 | - | https://arxiv.org/html/2012.07450v1 |
| - | 2102.09030 | Proactive DP: A Multiple Target Optimization Framework for D | 2021 | exclude | E2 | - | https://arxiv.org/html/2102.09030v10 |
| - | 2201.13320 | BEER: Fast $O(1/T)$ Rate for Decentralized Nonconvex Optimiz | 2022 | exclude | E2 | - | https://arxiv.org/html/2201.13320v3 |
| - | 2204.06760 | HCFL: A High Compression Approach for Communication-Efficien | 2022 | exclude | E2 | - | https://arxiv.org/html/2204.06760v2 |
| - | 2207.04338 | Variance Reduced ProxSkip: Algorithm, Theory and Application | 2022 | exclude | E2 | - | https://arxiv.org/html/2207.04338v1 |
| - | 2211.14391 | MDA: Availability-Aware Federated Learning Client Selection | 2022 | exclude | E2 | - | https://arxiv.org/html/2211.14391v1 |
| - | 2302.03662 | Federated Learning with Regularized Client Participation | 2023 | exclude | E2 | - | https://arxiv.org/html/2302.03662v2 |
| - | 2302.04208 | Exploratory Analysis of Federated Learning Methods with Diff | 2023 | exclude | E2 | - | https://arxiv.org/html/2302.04208v1 |
| - | 2305.12316 | One-Shot Federated Learning for LEO Constellations that Redu | 2023 | exclude | E2 | - | https://arxiv.org/html/2305.12316v1 |
| - | 2402.09095 | FedSiKD: Clients Similarity and Knowledge Distillation: Addr | 2024 | exclude | E2 | - | https://arxiv.org/html/2402.09095v1 |
| - | 2402.15166 | Convergence Analysis of Split Federated Learning on Heteroge | 2024 | exclude | E2 | - | https://arxiv.org/html/2402.15166v3 |
| - | 2403.04144 | FedClust: Optimizing Federated Learning on Non-IID Data Thro | 2024 | exclude | E2 | - | https://arxiv.org/html/2403.04144v1 |
| - | 2403.12329 | FedFisher: Leveraging Fisher Information for One-Shot Federa | 2024 | exclude | E2 | - | https://arxiv.org/html/2403.12329v1 |
| - | 2002.05516 | Federated Learning of a Mixture of Global and Local Models | 2020 | exclude | E3(c) | - | https://arxiv.org/html/2002.05516v3 |
| - | 2006.06983 | Characterizing Impacts of Heterogeneity in Federated Learnin | 2021 | exclude | E2 | - | https://arxiv.org/html/2006.06983v4 |
| - | 2008.05189 | Dispersed Federated Learning: Vision, Taxonomy, and Future D | 2021 | exclude | E2 | - | https://arxiv.org/html/2008.05189v2 |
| - | 2011.11266 | Federated Learning with Class Imbalance Reduction | 2021 | exclude | E2 | - | https://arxiv.org/html/2011.11266v1 |
| - | 2012.14453 | Straggler-Resilient Federated Learning: Leveraging the Inter | 2020 | exclude | E3(c) | - | https://arxiv.org/html/2012.14453v1 |
| - | 2103.01319 | Adversarial training in communication constrained federated  | 2021 | exclude | E2 | - | https://arxiv.org/html/2103.01319v1 |
| - | 2104.11320 | Federated Double Deep Q-learning for Joint Delay and Energy  | 2021 | exclude | E2 | - | https://arxiv.org/html/2104.11320v1 |
| - | 2106.06639 | Federated Learning with Buffered Asynchronous Aggregation | 2021 | exclude | E3(d) | - | https://arxiv.org/html/2106.06639v4 |
| - | 2111.02791 | Cyber Threat Intelligence Sharing Scheme Based on Federated  | 2022 | exclude | E2 | - | https://arxiv.org/html/2111.02791v1 |
| - | 2111.03396 | FedLess: Secure and Scalable Federated Learning Using Server | 2021 | exclude | E3(d) | - | https://arxiv.org/html/2111.03396v1 |
| - | 2111.14683 | Anomaly Localization in Model Gradients Under Backdoor Attac | 2021 | exclude | E2 | - | https://arxiv.org/html/2111.14683v1 |
| - | 2202.07391 | Exploring Deep Reinforcement Learning-Assisted Federated Lea | 2022 | exclude | E2 | - | https://arxiv.org/html/2202.07391v2 |
| - | 2203.10708 | A comprehensive review on blockchains for Internet of Vehicl | 2023 | exclude | E2 | - | https://arxiv.org/html/2203.10708v1 |
| - | 2203.11834 | Improving Generalization in Federated Learning by Seeking Fl | 2022 | exclude | E2 | - | https://arxiv.org/html/2203.11834v3 |
