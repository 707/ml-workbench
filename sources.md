# Token Tax Calculator — Research Sources

## Core Papers (sorted by applied AI importance)

### 1. Reducing Tokenization Premiums for Low-Resource Languages in LLMs (2026)
- **Link**: https://arxiv.org/abs/2601.13328
- **Key finding**: Defines "tokenization premiums" for low-resource languages, quantifies 3-4x penalties across 10 popular LMs
- **Actionable**: Proposes adding new tokens/embeddings to frozen models as practical mitigation (no retraining)

### 2. The Token Tax: Systematic Bias in Multilingual Tokenization (ACL/AfricanNLP 2026)
- **Links**: https://arxiv.org/abs/2509.05486 | https://aclanthology.org/2026.africanlp-main.10.pdf
- **Key finding**: 2-5x token inflation → 4-25x training compute cost (O(n²) scaling); higher fertility predicts lower accuracy on AfriMMLU
- **Actionable**: Concrete cost tables for LLaMA-style models and per-million-token API pricing scenarios

### 3. Tokenization Disparities as Infrastructure Bias (2025)
- **Links**: https://arxiv.org/abs/2510.12389 | https://arxiv.org/html/2510.12389v1
- **Key finding**: 200+ language study (FLORES-200); Latin-script languages efficient, many non-Latin 3-5x higher RTC
- **Actionable**: Introduces Relative Tokenization Cost (RTC) as normalized cross-lingual metric

### 4. The Art of Breaking Words: Rethinking Multilingual Tokenizer Design (2025)
- **Link**: https://arxiv.org/abs/2508.06533
- **Key finding**: Redesigned multilingual tokenizer yields >40% improvement in token-to-word ratio for Indic languages
- **Actionable**: Better tokenization alone improves performance AND inference speed

### 5. EfficientXLang: Towards Improving Token Efficiency for Multilingual Reasoning (2025)
- **Link**: https://arxiv.org/pdf/2507.00246.pdf
- **Key finding**: Multilingual reasoning can yield shorter but equally effective reasoning traces
- **Actionable**: Language switching mid-chain can save tokens in agent frameworks

### 6. Tokenization Optimization for Low-Resource Languages (2025)
- **Link**: https://arxiv.org/abs/2412.06926
- **Key finding**: Proposes tokenization modification for low-resource languages to optimize inference time/cost
- **Actionable**: Bridges tokenization metrics to concrete deployment trade-offs

### 7. Sawtone: Universal Framework for Phonetic Similarity and Alignment (2025)
- **Link**: https://pressto.amu.edu.pl/index.php/linpo/article/view/52264/42710
- **Author**: Omar Kamali (Omneity Labs)
- **Key finding**: For low-resource/dialectal languages, orthographic messiness (non-standard spelling, mixed scripts, alloglottography) adds a "messiness tax" on top of the tokenization tax
- **Actionable**: Phonetic-aware normalization can collapse spelling variants → fewer tokens; tool should separate "core token tax" from "normalization tax"

### 8. Goldfish: Monolingual Language Models for 350 Languages (2024-2025)
- **Link**: https://arxiv.org/html/2408.10441v2
- **Key finding**: Small monolingual models (125M, custom 50k tokenizers) often outperform big multilingual models in perplexity/grammaticality for low-resource languages
- **Actionable**: Byte premiums (UTF-8 bytes vs English) as more fundamental measure; custom monolingual models can be cheaper at scale

## Additional References

- **Democracy and AI language access**: https://www.techpolicy.press/when-ai-cant-understand-your-language-democracy-breaks-down-/
- **Multilingual curation for frontier corpus** (2026): https://arxiv.org/abs/2601.18026
- **Prior art — tokka-bench**: https://github.com/bgub/tokka-bench (CLI benchmarking tool for 100+ languages)
- **Reddit discussion**: https://old.reddit.com/r/MachineLearning/comments/1n0r8b7/i_built_a_tool_to_benchmark_tokenizers_across_100/

## Key Metrics from Literature

| Metric | Source | Definition |
|--------|--------|------------|
| Relative Tokenization Cost (RTC) | Tokenization Disparities paper | source_tokens / english_tokens for equivalent content |
| Token Fertility | Token Tax paper | tokens per word for a given language/tokenizer |
| Byte Premium | Goldfish paper | UTF-8 bytes / ASCII-equivalent English bytes |
| Tokenization Premium | Reducing Premiums paper | excess tokens vs English for same semantic content |

## Key Insight: Problem is NOT Solved

2026 papers confirm:
- Frontier reasoning models (DeepSeek, o1) narrow accuracy gaps but inherit same tokenization constraints
- Larger vocabularies (Gemma ~250k, Qwen) reduce extreme fragmentation but don't solve script-specific issues
- Post-hoc vocabulary surgery works but is not widely adopted
- No single model natively handles all target languages well

## Tool Design Implications

1. **From diagnosis to decision support**: Don't just show the tax; recommend mitigations
2. **Three business harms**: higher spend + less usable context + potentially worse quality
3. **Stakeholder-specific views**: engineers need export/CLI, PMs need projections, managers need ROI
4. **Phonetic/orthographic dimension** (Sawtone): separate "token tax" from "messiness tax"
5. **Monolingual alternative** (Goldfish): show when building a custom model pays for itself
6. **Portfolio view**: aggregate across real traffic, not just single paragraphs
