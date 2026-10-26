# Re-check: do any of the 58 report trajectory stability?

Re-checker: single-agent re-read of the downloaded full texts (2026-10-19), independent of the original extraction pass.
Script: `src/recheck_stability.py`. Pattern tiers are defined in the script docstring: only a TIGHT hit (an explicit statement about behaviour across ROUNDS near the target) can overturn the 0/58 claim; LOOSE dispersion notation is reported for contrast because 46/58 studies print some.

| study | full text matched | TIGHT hits | LOOSE dispersion |
|---|---|---|---|
| S001 Federated Multi-Mini-Batch: An Efficient Training Approach to Federate | 2011.07006.txt | - | - |
| S002 Clustered Scheduling and Communication Pipelining for Efficient Resour | 2206.07631.txt | - | any dispersion notation(3) |
| S003 Digital Twin-Driven Communication-Efficient Federated Anomaly Detectio | 2601.01701.txt | - | any dispersion notation(3) |
| S004 VARS-FL: Validation-Aligned Client Selection for Non-IID Federated Lea | 2605.05896.txt | oscillation(3) | any dispersion notation(8) |
| S005 FedADMM: A Robust Federated Deep Learning Framework with Adaptivity to | 2204.03529.txt | oscillation(3) | any dispersion notation(1) |
| S006 GTFLAT: Game Theory Based Add-On For Empowering Federated Learning Agg | 2212.04103.txt | - | - |
| S007 Flashback: Understanding and Mitigating Forgetting in Federated Learni | 2402.05558.txt | final/last-k-round spread(1) | - |
| S008 NTK-DFL: Enhancing Decentralized Federated Learning in Heterogeneous S | 2410.01922.txt | final/last-k-round spread(1), holds / sustains the target(1) | any dispersion notation(15) |
| S009 Communication-Efficient Neural Tangent Kernels for Heterogeneous Decen | 2512.12737.txt | final/last-k-round spread(1) | any dispersion notation(6) |
| S010 Distributionally Robust Federated Learning With Client Drift Minimizat | 2505.15371.txt | - | any dispersion notation(47) |
| S011 FedSA: Accelerating Intrusion Detection in Collaborative Environments  | 2205.11519.txt | final/last-k-round spread(1) | any dispersion notation(2) |
| S012 Federated Learning for Keyword Spotting | 1810.05512.txt | - | any dispersion notation(2) |
| S013 Adaptive Privacy Budget Allocation for Differential Privacy Optimizati | 10.69987_aimlr.2026.70102.txt | final/last-k-round spread(3) | any dispersion notation(3) |
| S014 Federated Learning for Malicious Domain Detection via Privacy-Preservi | 10.32604_cmc.2026.077337.txt | - | any dispersion notation(7) |
| S016 FedDCT: Federated Learning of Large Convolutional Neural Networks on R | 2211.10948.txt | - | - |
| S017 FAGH: Accelerating Federated Learning with Approximated Global Hessian | 2403.11041.txt | - | any dispersion notation(1) |
| S018 LEFL: Low Entropy Client Sampling in Federated Learning | 2312.17430.txt | - | any dispersion notation(2) |
| S019 Power-Efficient Over-the-Air Aggregation With Receive Beamforming for  | 2501.18058.txt | - | any dispersion notation(9) |
| S020 Energy Efficient Federated Learning with Hyperdimensional Computing ov | 2602.21949.txt | oscillation(1) | any dispersion notation(8) |
| S021 Communication-Efficient Federated Learning under Non-IID Data: Aggrega | 10.54254_2755-2721_2026.37334.txt | - | any dispersion notation(3) |
| S026 Speeding up Heterogeneous Federated Learning with Sequentially Trained | 2201.10899.txt | final/last-k-round spread(1) | any dispersion notation(4) |
| S027 Fed-BAC: Federated Bandit-Guided Additive Clustering in Hierarchical F | - | - | - |
| S028 FedEff: efficient federated learning with optimal local epochs for het | 10.1038_s41598-025-22672-1.txt | - | any dispersion notation(3) |
| S029 A federated learning framework for Non-IID data : data feature optimiz | 10.1038_s41598-026-74398-3.txt | final/last-k-round spread(1) | any dispersion notation(2) |
| S030 Achieving consistency in FedSAM using local adaptive distillation on s | 10.1371_journal.pone.0333210.txt | final/last-k-round spread(1) | any dispersion notation(9) |
| S032 Dataset-centric evaluation of federated intrusion detection models in  | 10.1038_s41598-025-32567-w.txt | oscillation(3) | any dispersion notation(14) |
| S033 Federated Learning with Additional Mechanisms on Clients to Reduce Com | 1908.05891.txt | final/last-k-round spread(1) | any dispersion notation(1) |
| S034 Fast-Convergent Federated Learning | 2007.13137.txt | - | any dispersion notation(4) |
| S035 Fast-Convergent Federated Learning with Adaptive Weighting | 2012.00661.txt | - | any dispersion notation(2) |
| S036 Contextual Model Aggregation for Fast and Robust Federated Learning in | 2203.12738.txt | - | - |
| S037 Time-Triggered Federated Learning Over Wireless Networks | 2204.12426.txt | - | - |
| S038 FedEntropy: Efficient Device Grouping for Federated Learning Using Max | 2205.12038.txt | final/last-k-round spread(1) | any dispersion notation(2) |
| S039 Enhancing Heterogeneous Federated Learning with Knowledge Extraction a | 2208.07978.txt | - | any dispersion notation(2) |
| S040 On-Demand-FL: A Dynamic and Efficient Multicriteria Federated Learning | 2211.02906.txt | - | any dispersion notation(2) |
| S041 Communication-Efficient Federated Learning for Heterogeneous Edge Devi | 2212.08272.txt | final/last-k-round spread(3) | - |
| S042 FedAVO: Improving Communication Efficiency in Federated Learning with  | 2305.01154.txt | oscillation(1) | - |
| S043 An Efficient Virtual Data Generation Method for Reducing Communication | 2306.12088.txt | - | any dispersion notation(1) |
| S044 FLASH-RL: Federated Learning Addressing System and Static Heterogeneit | 2311.06917.txt | oscillation(1) | any dispersion notation(1) |
| S045 Communication-Efficient Federated Optimization over Semi-Decentralized | 2311.18787.txt | final/last-k-round spread(1) | any dispersion notation(9) |
| S046 FedClust: Tackling Data Heterogeneity in Federated Learning through We | 2407.07124.txt | - | any dispersion notation(3) |
| S047 Exploiting Adaptive Channel Pruning for Communication-Efficient Split  | 2603.09792.txt | - | - |
| S051 Federated Learning with Unbiased Gradient Aggregation and Controllable | 1910.08234.txt | final/last-k-round spread(4) | any dispersion notation(2) |
| S052 Federated Generalized Bayesian Learning via Distributed Stein Variatio | 2009.06419.txt | - | any dispersion notation(5) |
| S053 FedProf: Selective Federated Learning with Representation Profiling | 2102.01733.txt | final/last-k-round spread(1) | any dispersion notation(8) |
| S054 Precision‐Weighted Federated Learning | 2107.09627.txt | final/last-k-round spread(1) | any dispersion notation(45) |
| S055 Neural Tangent Kernel Empowered Federated Learning | 2110.03681.txt | - | any dispersion notation(1) |
| S056 Federated Semi-Supervised Learning with Class Distribution Mismatch | 2111.00010.txt | final/last-k-round spread(2) | any dispersion notation(27) |
| S057 Heterogeneous Federated Learning via Grouped Sequential-to-Parallel Tr | 2201.12976.txt | - | - |
| S058 Efficient Federated Learning on Knowledge Graphs via Privacy-preservin | 2203.09553.txt | - | any dispersion notation(1) |
| S059 UNIDEAL: Curriculum Knowledge Distillation Federated Learning | 2309.08961.txt | final/last-k-round spread(2) | any dispersion notation(1) |
| S060 Mobility Accelerates Learning: Convergence Analysis on Hierarchical Fe | 2401.09656.txt | final/last-k-round spread(4), oscillation(1) | any dispersion notation(1) |
| S061 Federated Learning in Mobile Edge Networks: A Comprehensive Survey | 1909.11875.txt | - | any dispersion notation(4) |
| S062 Improving Federated Learning Personalization via Model Agnostic Meta L | 1909.12488.txt | - | any dispersion notation(7) |
| S063 From Deterioration to Acceleration: A Calibration Approach to Rehabili | 2112.09355.txt | - | any dispersion notation(12) |
| S064 Deep Reinforcement Learning Assisted Federated Learning Algorithm for  | 2202.03575.txt | - | any dispersion notation(1) |
| S065 Fine-tuning Global Model via Data-Free Knowledge Distillation for Non- | 2203.09249.txt | - | any dispersion notation(3) |
| S066 FedDC: Federated Learning with Non-IID Data via Local Drift Decoupling | 2203.11751.txt | final/last-k-round spread(4) | any dispersion notation(12) |
| S067 ADDS: Adaptive Differentiable Sampling for Robust Multi-Party Learning | 2110.15522.txt | - | any dispersion notation(3) |

## Verdict

* studies matched to a downloaded full text: **57 / 58**
* studies with any TIGHT hit: **25**
* studies with any LOOSE dispersion notation: **47**

Unmatched studies are reported as such and are NOT counted as evidence for 0/58: a missing file is not a negative finding.
