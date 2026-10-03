## 2. Related work

Several literatures touch this problem. None occupies quite the position this benchmark
takes, but three recent benchmarks come closer than a reader of the introduction might
expect, and we say where. In each case the difference lies in what the system is given,
what it must return, and how the label is established.

**Legal and regulatory NLP benchmarks.** Work in this area evaluates reasoning and
classification over *legal text*. LegalBench assembles 162 tasks spanning six types of
legal reasoning, designed and hand-crafted by legal professionals (Guha et al., 2023).
LexGLUE standardises a collection of legal language-understanding datasets (Chalkidis et
al., 2022); CaseHOLD poses over 53,000 multiple-choice questions identifying the holding
of a cited case (Zheng et al., 2021); CUAD asks models to highlight salient portions
of contracts, with over 13,000 annotations from legal experts (Hendrycks et al., 2021); and
LawBench tests legal knowledge at the levels of memorisation, understanding and
application (Fei et al., 2024). A system is given a legal question or a document and
asked to answer, classify, or retrieve. Our input is an organisation's structured
operational records, and our output is a verdict per obligation about that organisation.
A model that scores well on legal reasoning has demonstrated nothing about whether it
will report an unassessable duty as satisfied, because these tasks do not ask it to
decide whether its evidence base is sufficient.

The legal hallucination literature is closer in motivation. Dahl et al. (2024) find
hallucination rates between 58% and 88% when models are asked verifiable questions about
federal court cases, and report that models cannot always predict when they are
hallucinating. Magesh et al. (2025), in a preregistered evaluation, find that commercial
legal research tools hallucinate less than a general-purpose chatbot but substantially
more than their vendors claim. Both measure unsupported output about the law. We measure
unsupported output about a regulated party, where the support that is missing is a record
rather than a precedent.

**Immigration-specific datasets.** ImmigrationQA provides 17,058 question-answer pairs
generated from United States immigration sources including the USCIS Policy Manual and
8 CFR (Shportun, 2026). ImmigrationReason structures 12,375 non-precedent decisions of the
USCIS Administrative Appeals Office, recording for each the applicable legal framework,
per-criterion evidence-sufficiency findings under a five-category label, and verbatim
adjudicator criticism, including nearly 9,000 instances of legal error identified by the
Office (Afsharrad and Mousavi, 2026). ImmigrationReason is nearer to our task than a
policy-QA dataset, since it labels whether evidence sufficed for a criterion. Its labels,
however, are extracted from the text of adjudications: the sufficiency judgement is the
adjudicator's, made about a petition record that the dataset does not contain. Both
datasets are text-side. Employer-side obligations, where the per-worker civil penalties and
the audit exposure sit, are absent. We are not aware of a public dataset of employer
immigration-compliance records with labelled obligation outcomes, and the reason is
straightforward: real ones cannot be published.

**Compliance benchmarks for AI systems.** Automated compliance checking predates language
models. In construction, regulatory text is converted into machine-checkable rules by
semantic information extraction (Zhang and El-Gohary, 2016); in data protection, privacy
policies are checked for completeness against GDPR provisions (Amaral et al., 2022) and
questioned directly, with expert analysis of which questions a policy can answer at all
(Ravichander et al., 2019). Recent LLM work divides into two directions. In the first, the
AI system is the regulated subject: COMPL-AI translates the EU AI Act into technical
requirements and benchmarks twelve LLMs against them (Guldimann et al., 2024). The
direction of assessment is inverted relative to ours. In the second, the AI system is an
assessor of someone else. HSE-Bench poses over 1,000 IRAC-structured health, safety and
environment compliance questions (Wang et al., 2025). Principle-Bench evaluates LLM judges
of financial promotions against two regulatory principles under a pre-registered rubric
(Sarkar, 2026). ReguSim's monitoring benchmark asks a model to judge a marked record within
a window of trading records, and finds that simple structured baselines match or exceed
prompt-only LLMs (Luo et al., 2026). These share our assessor-side orientation, and the
last shares our record-level input. None of them gives insufficiency of the record its
own correct label.

Two recent benchmarks do, and they are the nearest neighbours of this work. DEMM-Bench
asks whether agent-runtime records (traces, ledgers, policy logs and the like) are
sufficient to reconstruct properties of a specific decision, labels cases with a
construction oracle, and reports an overclaim rate as its primary diagnostic (Solozobov,
2026). Its "container fallacy", treating the presence of an evidence container as
sufficiency, is close to what we call adjacent-field substitution, where a populated column
beside the missing evidence is read as the evidence. Partial Evidence Bench constructs
deterministic synthetic scenarios, including a compliance-audit family, in which material
evidence lies outside an agent's authorisation boundary, and scores *unsafe completeness*:
an answer that appears complete when it is not (Tallam, 2026). It reports that explicit
fail-and-report behaviour removes unsafe completeness without collapsing into trivial
abstention. That is, in substance, our argument that the false-green rate and the
abstention rate must be read together. We differ in three respects. Our subject is a
third-party employer and our output a regulatory verdict per (obligation, entity) pair,
not a governance reconstruction or a retrieval answer; our insufficiency is a property of
what the employer's exports contain, not of what an agent is permitted to see; and our
scale (58,961 pairs over 31 firms, against 64 cases and 72 tasks respectively) supports per-firm
aggregation and intervals. We do not claim the directional, construction-labelled framing
as new; both works reach it independently.

**Abstention and selective prediction.** This is the closest established literature and
deserves the most precision, because a reviewer will reasonably ask what is new.

The reject option goes back to Chow (1970), who characterised the optimal tradeoff between
recognition error and rejection. Selective classification formalises it as a risk-coverage
trade-off (El-Yaniv and Wiener, 2010), and Geifman and El-Yaniv (2017) construct selective
deep classifiers that reject as needed to meet a user-set risk level. In this framing
coverage is a good to be maximised subject to a risk budget, and abstention is a *cost*
incurred to avoid error.

For language models, abstention is evaluated mostly on questions. SQuAD 2.0 adds
unanswerable questions to reading comprehension (Rajpurkar et al., 2018); SelfAware pairs
unanswerable questions with answerable counterparts to measure self-knowledge (Yin et al.,
2023); AbstentionBench aggregates 20 datasets of unknown-answer, underspecified,
false-premise and similar questions, and finds that scaling helps little and that
reasoning fine-tuning degrades abstention by 24% on average (Kirichenko et al., 2025). Wen
et al. (2025) survey the area and organise it by query, model and human values. On the
model side, Kadavath et al. (2022) show that models can be trained to predict whether they
know an answer. The work nearest ours in this line is Joren et al. (2024), who define
whether a retrieved context is *sufficient* to answer a query and find that strong models
often answer incorrectly rather than abstain when it is not. That is a statement about the
evidence base rather than the query, as ours is, though in open-domain retrieval rather
than over an organisation's records. Hallucination benchmarks that measure falsehood
against world knowledge (Lin et al., 2022) or the share of atomic claims supported by a
knowledge source (Min et al., 2023) address a related failure without an abstention
label.

Three things differ here.

First, abstention is not a cost. For 45.3% of pairs in our released set it is the
*correct output*, and it is actionable: `needs_evidence` names a document the firm must
produce. A system that trades abstention for coverage is not moving along a tradeoff
curve, it is producing wrong answers that happen to look like answers.

Second, insufficiency is a property of the evidence base rather than the query, so it is
determinable **by construction**. The generator withholds a required field and the label
follows mechanically. Most abstention benchmarks annotate insufficiency, and annotation of
legal sufficiency is exactly the judgement call that makes such datasets small and
contestable. Joren et al. (2024) and the two benchmarks above are partial exceptions: the
first classifies sufficiency with an autorater, the latter two fix it by construction.

Third, the error is directional in a way the risk-coverage framing does not capture.
Answering `fail` on an undecidable pair is wrong but triggers review. Answering `pass` is
wrong and *suppresses* review. Aggregating both into a single risk term hides the only
distinction that matters operationally, which is why we report the false-green rate as a
separate quantity rather than as one minus abstention recall.

**Reasoning over structured and tabular data.** Table-based fact verification asks whether
a statement is entailed or refuted by a table (Chen et al., 2020), and text-to-SQL asks a
system to answer questions over relational databases (Yu et al., 2018). Both originally
assumed that every item could be decided. The three-way label of FEVER, with Supported,
Refuted and NotEnoughInfo assigned by annotators (Thorne et al., 2018), is the nearest
label structure to `pass`, `fail` and `needs_evidence`; FEVEROUS extends it to evidence in
table cells (Aly et al., 2021). Unanswerable questions over structured data appear in
EHRSQL, a text-to-SQL benchmark over electronic health records (Lee et al., 2022), in work
categorising ambiguous and unanswerable text-to-SQL questions (Wang et al., 2023), and in
TrustSQL, which scores abstention on infeasible questions with penalties for incorrect
output (Lee et al., 2024). ClaimDB is the closest: claims verified against real
multi-table databases, with a not-enough-info class, and a finding that both open and
closed models struggle to abstain when there is no evidence to decide (Theologitis et al.,
2026). Our setting shares the structured input and the insufficiency class. It differs in
that the item to be decided is a regulatory obligation attached to an entity rather than a
natural-language claim or question, in that labels are fixed by a generator rather than
annotated or derived from real databases, and in that the two wrong answers on an
undecidable item are scored asymmetrically.

**Output format and schema constraints.** Our schema ablation removes one permitted
verdict and leaves everything else fixed. Related work shows that output constraints
change model answers. Tam et al. (2024) find that restricting generation to structured
formats degrades reasoning, more so as constraints tighten. Röttger et al. (2024) show that
models forced into a multiple-choice format give substantively different answers from those
they give unforced, and that the answers depend on how they are forced. Sclar et al. (2024)
report swings of up to 76 accuracy points from meaning-preserving changes to prompt format,
which is one reason our prompt is frozen and identical across conditions. Closest in
argument is Kalai et al. (2025), who attribute persistent hallucination partly to grading
that gives no credit for expressing uncertainty, so that guessing improves scores, and
propose changing how existing benchmarks are scored. Our ablation is an instance of the
same incentive located in a product interface rather than a leaderboard: a schema with no
state for "could not tell" forces a guess, and some guesses are green. We are not aware of
prior work that measures the effect of removing the abstention label alone on a
directional error rate.

**Aggregate consistency.** We searched for prior work measuring whether a system's reported
headline counts agree with its own per-item outputs and did not find any. We include it as
a metric because we have observed the failure in deployed compliance dashboards, where a
card and its drilldown disagree; we flag it as the least-established axis in the suite.

**Positioning, stated plainly.** The contribution is not a new abstention algorithm and
not a theoretical result. Nor is it the first benchmark to fix evidence insufficiency by
construction or to score the overclaiming direction separately: DEMM-Bench and Partial
Evidence Bench do both, in agent governance and authorisation-limited retrieval. What this
benchmark adds is a task in which correct abstention is the majority class and the
assessed party is a third-party employer described by structured exports; an instrument
for the directional error in that setting, together with an ablation that isolates how
much of it is produced by the output schema; and a releasable artifact in a domain where
releasability is the binding constraint. Ground truth by construction has precedent in
synthetic task suites such as bAbI (Weston et al., 2015); here it also means fresh firms
can be drawn at any seed, which addresses the per-benchmark contamination concern raised
by Sainz et al. (2023). Constructed labels are not error-free, and test-set label errors
can change model rankings (Northcutt et al., 2021), which is why we audit the withheld
labels (Section 6). The release follows datasheet practice (Gebru et al., 2021), and our
reporting requirement, that the false-green rate always appear beside violation recall, is
in the spirit of model cards (Mitchell et al., 2019). Section 10 states what this does not
establish.

---

## References

Afsharrad, A. and Mousavi, S. S. (2026). ImmigrationReason: A Structured Dataset of U.S. Immigration Appeals for Legal Reasoning Research. arXiv preprint arXiv:2608.20391. https://arxiv.org/abs/2608.20391

Aly, R., Guo, Z., Schlichtkrull, M., Thorne, J., Vlachos, A., Christodoulopoulos, C., Cocarascu, O. and Mittal, A. (2021). FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2106.05707

Amaral, O., Abualhaija, S., Torre, D., Sabetzadeh, M. and Briand, L. C. (2022). AI-enabled Automation for Completeness Checking of Privacy Policies. IEEE Transactions on Software Engineering 48(11). https://doi.org/10.1109/TSE.2021.3124332

Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D. M. and Aletras, N. (2022). LexGLUE: A Benchmark Dataset for Legal Language Understanding in English. Proceedings of ACL 2022. https://aclanthology.org/2022.acl-long.297

Chen, W., Wang, H., Chen, J., Zhang, Y., Wang, H., Li, S., Zhou, X. and Wang, W. Y. (2020). TabFact: A Large-scale Dataset for Table-based Fact Verification. ICLR 2020. https://arxiv.org/abs/1909.02164

Chow, C. (1970). On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory 16(1):41-46. https://doi.org/10.1109/TIT.1970.1054406

Dahl, M., Magesh, V., Suzgun, M. and Ho, D. E. (2024). Large Legal Fictions: Profiling Legal Hallucinations in Large Language Models. Journal of Legal Analysis 16(1):64-93. https://arxiv.org/abs/2401.01301

El-Yaniv, R. and Wiener, Y. (2010). On the Foundations of Noise-free Selective Classification. Journal of Machine Learning Research 11:1605-1641. https://jmlr.org/papers/v11/el-yaniv10a.html

Fei, Z., Shen, X., Zhu, D., Zhou, F., Han, Z., Zhang, S., Chen, K., Shen, Z. and Ge, J. (2024). LawBench: Benchmarking Legal Knowledge of Large Language Models. Proceedings of EMNLP 2024. https://aclanthology.org/2024.emnlp-main.452

Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé, H. and Crawford, K. (2021). Datasheets for Datasets. Communications of the ACM 64(12). https://doi.org/10.1145/3458723

Geifman, Y. and El-Yaniv, R. (2017). Selective Classification for Deep Neural Networks. Advances in Neural Information Processing Systems 30. https://arxiv.org/abs/1705.08500

Guha, N., Nyarko, J., Ho, D. E., Ré, C., et al. (2023). LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models. NeurIPS 2023 Datasets and Benchmarks Track. https://arxiv.org/abs/2308.11462

Guldimann, P., Spiridonov, A., Staab, R., Jovanović, N., Vero, M., Vechev, V., Gueorguieva, A.-M., Balunović, M., Konstantinov, N., Bielik, P., Tsankov, P. and Vechev, M. (2024). COMPL-AI Framework: A Technical Interpretation and LLM Benchmarking Suite for the EU Artificial Intelligence Act. arXiv preprint arXiv:2410.07959. https://arxiv.org/abs/2410.07959

Hendrycks, D., Burns, C., Chen, A. and Ball, S. (2021). CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.06268

Joren, H., Zhang, J., Ferng, C.-S., Juan, D.-C., Taly, A. and Rashtchian, C. (2024). Sufficient Context: A New Lens on Retrieval Augmented Generation Systems. arXiv preprint arXiv:2411.06037. https://arxiv.org/abs/2411.06037

Kadavath, S., Conerly, T., Askell, A., Henighan, T., Drain, D., Perez, E., et al. (2022). Language Models (Mostly) Know What They Know. arXiv preprint arXiv:2207.05221. https://arxiv.org/abs/2207.05221

Kalai, A. T., Nachum, O., Vempala, S. S. and Zhang, E. (2025). Why Language Models Hallucinate. arXiv preprint arXiv:2509.04664. https://arxiv.org/abs/2509.04664

Kirichenko, P., Ibrahim, M., Chaudhuri, K. and Bell, S. J. (2025). AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. arXiv preprint arXiv:2506.09038. https://arxiv.org/abs/2506.09038

Lee, G., Chay, W., Cho, S. and Choi, E. (2024). TrustSQL: Benchmarking Text-to-SQL Reliability with Penalty-Based Scoring. arXiv preprint arXiv:2403.15879. https://arxiv.org/abs/2403.15879

Lee, G., Hwang, H., Bae, S., Kwon, Y., Shin, W., Yang, S., Seo, M., Kim, J.-Y. and Choi, E. (2022). EHRSQL: A Practical Text-to-SQL Benchmark for Electronic Health Records. NeurIPS 2022 Datasets and Benchmarks Track. https://arxiv.org/abs/2301.07695

Lin, S., Hilton, J. and Evans, O. (2022). TruthfulQA: Measuring How Models Mimic Human Falsehoods. Proceedings of ACL 2022. https://aclanthology.org/2022.acl-long.229

Luo, Y., Jiang, Y., Xie, Q., Lan, L., Cong, L. W., Rao, A. and Song, Y. (2026). ReguSim: Evaluating LLM Agent Rule Grounding in Financial Compliance. arXiv preprint arXiv:2608.19974. https://arxiv.org/abs/2608.19974

Magesh, V., Surani, F., Dahl, M., Suzgun, M., Manning, C. D. and Ho, D. E. (2025). Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools. Journal of Empirical Legal Studies 22(2). https://doi.org/10.1111/jels.12413

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L. and Hajishirzi, H. (2023). FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. Proceedings of EMNLP 2023. https://aclanthology.org/2023.emnlp-main.741

Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D. and Gebru, T. (2019). Model Cards for Model Reporting. Proceedings of FAT* 2019. https://doi.org/10.1145/3287560.3287596

Northcutt, C. G., Athalye, A. and Mueller, J. (2021). Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.14749

Rajpurkar, P., Jia, R. and Liang, P. (2018). Know What You Don't Know: Unanswerable Questions for SQuAD. Proceedings of ACL 2018. https://aclanthology.org/P18-2124

Ravichander, A., Black, A. W., Wilson, S., Norton, T. and Sadeh, N. (2019). Question Answering for Privacy Policies: Combining Computational and Legal Perspectives. Proceedings of EMNLP-IJCNLP 2019. https://aclanthology.org/D19-1500

Röttger, P., Hofmann, V., Pyatkin, V., Hinck, M., Kirk, H. R., Schütze, H. and Hovy, D. (2024). Political Compass or Spinning Arrow? Towards More Meaningful Evaluations for Values and Opinions in Large Language Models. Proceedings of ACL 2024. https://aclanthology.org/2024.acl-long.816

Sainz, O., Campos, J. A., García-Ferrero, I., Etxaniz, J., Lopez de Lacalle, O. and Agirre, E. (2023). NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark. Findings of EMNLP 2023. https://aclanthology.org/2023.findings-emnlp.722

Sarkar, D. (2026). A Four-Axis Trustworthiness Benchmark for LLM-as-Judge in Principle-Based Regulation. KDD 2026 Workshop on Secure and Trustworthy Large Language Models. arXiv:2608.14329. https://arxiv.org/abs/2608.14329

Sclar, M., Choi, Y., Tsvetkov, Y. and Suhr, A. (2024). Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting. ICLR 2024. https://arxiv.org/abs/2310.11324

Shportun, N. (2026). ImmigrationQA: A Source-Grounded Dataset and Small-Model Adaptation for U.S. Immigration Law. arXiv preprint arXiv:2605.30589. https://arxiv.org/abs/2605.30589

Solozobov, O. (2026). DEMM-Bench: A Cross-Regime Benchmark for Agent-Runtime Governance-Evidence Sufficiency. arXiv preprint arXiv:2606.20634. https://arxiv.org/abs/2606.20634

Tallam, K. (2026). Partial Evidence Bench: Benchmarking Authorization-Limited Evidence in Agentic Systems. arXiv preprint arXiv:2605.05379. https://arxiv.org/abs/2605.05379

Tam, Z. R., Wu, C.-K., Tsai, Y.-L., Lin, C.-Y., Lee, H. and Chen, Y.-N. (2024). Let Me Speak Freely? A Study On The Impact Of Format Restrictions On Large Language Model Performance. Proceedings of EMNLP 2024: Industry Track. https://aclanthology.org/2024.emnlp-industry.91

Theologitis, M., Dammu, P. P. S., Shah, C. and Suciu, D. (2026). ClaimDB: A Fact Verification Benchmark over Large Structured Data. ACL 2026. arXiv:2601.14698. https://arxiv.org/abs/2601.14698

Thorne, J., Vlachos, A., Christodoulopoulos, C. and Mittal, A. (2018). FEVER: a Large-scale Dataset for Fact Extraction and VERification. Proceedings of NAACL-HLT 2018. https://aclanthology.org/N18-1074

Wang, B., Gao, Y., Li, Z. and Lou, J.-G. (2023). Know What I don't Know: Handling Ambiguous and Unknown Questions for Text-to-SQL. Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.352

Wang, J., Wang, M., Zhou, Y., Xing, Z., Liu, Q., Xu, X., Zhang, W. and Zhu, L. (2025). LLM-based HSE Compliance Assessment: Benchmark, Performance, and Advancements. arXiv preprint arXiv:2505.22959. https://arxiv.org/abs/2505.22959

Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B. and Wang, L. L. (2025). Know Your Limits: A Survey of Abstention in Large Language Models. Transactions of the Association for Computational Linguistics. https://aclanthology.org/2025.tacl-1.26

Weston, J., Bordes, A., Chopra, S., Rush, A. M., van Merriënboer, B., Joulin, A. and Mikolov, T. (2015). Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks. arXiv preprint arXiv:1502.05698. https://arxiv.org/abs/1502.05698

Yin, Z., Sun, Q., Guo, Q., Wu, J., Qiu, X. and Huang, X. (2023). Do Large Language Models Know What They Don't Know? Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.551

Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z. and Radev, D. (2018). Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task. Proceedings of EMNLP 2018. https://aclanthology.org/D18-1425

Zhang, J. and El-Gohary, N. M. (2016). Semantic NLP-Based Information Extraction from Construction Regulatory Documents for Automated Compliance Checking. Journal of Computing in Civil Engineering 30(2). https://doi.org/10.1061/(ASCE)CP.1943-5487.0000346

Zheng, L., Guha, N., Anderson, B. R., Henderson, P. and Ho, D. E. (2021). When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset. ICAIL 2021. https://arxiv.org/abs/2104.08671
