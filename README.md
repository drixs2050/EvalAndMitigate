# Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests

[![DOI](https://zenodo.org/badge/1304820610.svg)](https://zenodo.org/badge/latestdoi/1304820610)

Replication package for the paper:

> Junda Zhao, Shurui Zhou, and Eldan Cohen. **Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests.** *Proceedings of the ACM on Software Engineering* 3, ISSTA, Article ISSTA113 (2026). DOI: [10.1145/3832204](https://doi.org/10.1145/3832204)

When an LLM is prompted with buggy code, it tends to generate **misguided tests** that assert the buggy behavior instead of exposing it. This package contains the full pipeline used in the paper to (1) measure this misguidance effect on Defects4J and (2) mitigate it with **specification-based test generation**, where the code under test in the prompt is replaced by an LLM-generated specification docstring.

The study uses Defects4J v3.0 (318 focal methods covering 233 defects across 17 Java projects) and evaluates 11 LLMs in 13 configurations. Every generated test is executed against **both** the buggy and the fixed project version and classified as:

| Category | Fixed version | Buggy version |
|---|---|---|
| True Negative | pass | pass |
| **Effective test** (True Positive) | pass | fail |
| **Misguided test** (False Negative) | fail | pass |
| False Positive | fail | fail |

The prompt-construction and evaluation harness is adapted from the LLM4UT project by Yang et al. (ASE 2024).

## Repository layout

| Path | Description |
|---|---|
| `checkout_all.sh`, `download_dependencies.sh`, `download_jar.ipynb` | One-time Defects4J setup |
| `generate_source_data_for_prompt.ipynb` | Extract focal-method data from Defects4J checkouts |
| `unify_fixed_and_buggy_bugs.ipynb` | Align buggy/fixed datasets to the same (bug, method) pairs |
| `Docstring_Generation.ipynb` | Generate **basic** specification docstrings |
| `Advanced_Docstring_Generation.ipynb` | Generate **advanced** (critical-analysis) docstrings |
| `generate_prompt.ipynb` | Build the test-generation prompts |
| `UT_Test_Generation.ipynb` | Call the LLM to generate unit tests |
| `UT_Compile_and_Test_fixed_project.ipynb` | Evaluate tests generated from **fixed** code |
| `UT_Compile_and_Test_Project.ipynb` | Evaluate tests generated from **buggy** code |
| `organize_seq_score_calc_json.ipynb`, `seq_score_calc.py` | Sequence-score (model-internal preference) analysis |
| `data/` | Defects4J fix metadata (`d4j2_fix_info/`), per-bug import/test-dir maps, tree-sitter grammar, shared config (`configuration.py`) |
| `utils/`, `rq1/` | Java parsing, prompt formatting, compilation/coverage helpers |
| `Prompt_example/` | Example prompts for docstring generation, test generation, and refinement |
| `section4.4_manual_inspection_results.xlsx` | Manual inspection results of generated docstrings (Section 4.4) |

## Requirements

- Linux, Java 11, Git, SVN (Defects4J prerequisites)
- [Defects4J v3.0](https://github.com/rjust/defects4j) installed and working (`defects4j info -p Lang` should succeed)
- Conda (the pipeline runs in Jupyter notebooks)
- An OpenAI API key (or another provider's key/client if you swap the model — see notes in each generation step)
- Only for the sequence-score analysis (`seq_score_calc.py`): a GPU machine able to serve the scoring model through [vLLM](https://github.com/vllm-project/vllm) (default scoring model: `openai/gpt-oss-120b`)

## 1. Setup

1. Install [Defects4J](https://github.com/rjust/defects4j) and verify it works.
2. Download the extra test-framework JARs (Mockito, JUnit 5, PowerMock, ...) into the Defects4J shared library directory:
   ```bash
   bash download_dependencies.sh /path/to/defects4j
   ```
3. Run [download_jar.ipynb](download_jar.ipynb) for the remaining JARs (JUnit 4.13.2, Mockito 5, PowerMock 2, ...). **Edit `LIB_DIR` at the top of the cell** to `/path/to/defects4j/framework/projects/lib` first.
4. From the **repository root**, check out all Defects4J projects (both buggy and fixed versions). This creates `d4j_proj_base/<Project>_<bug>/{buggy,fixed}/` and takes a long time and considerable disk space:
   ```bash
   bash checkout_all.sh
   ```
5. Create and activate the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate LLM4UT
   ```
6. Create the working directories used by the pipeline:
   ```bash
   mkdir -p data/prompts/rq1
   ```

## 2. Configure paths (read once, applies to everything below)

All machine-specific paths in this package use two placeholders:

| Placeholder | Replace with |
|---|---|
| `/path/to/repo` | the absolute path of this repository (so e.g. `d4j_proj_base` created in step 1.4 is at `/path/to/repo/d4j_proj_base`) |
| `/path/to/defects4j` | your Defects4J installation directory |

Replace them in:

- [data/configuration.py](data/configuration.py) (`d4j_home`, `d4j_proj_base`)
- [generate_source_data_for_prompt.ipynb](generate_source_data_for_prompt.ipynb) (`proj_base_dir`)
- [UT_Test_Generation.ipynb](UT_Test_Generation.ipynb) (prompt file paths, `defects4j` bin dir)
- [UT_Compile_and_Test_Project.ipynb](UT_Compile_and_Test_Project.ipynb) and [UT_Compile_and_Test_fixed_project.ipynb](UT_Compile_and_Test_fixed_project.ipynb) (data paths, `defects4j` bin dir, checkout dir, log/result paths)
- [organize_seq_score_calc_json.ipynb](organize_seq_score_calc_json.ipynb) (test-log input and pair-file output paths)

All notebooks assume the Jupyter kernel's working directory is the repository root (start `jupyter` from there). Note that importing `data/configuration.py` compiles the bundled tree-sitter Java grammar into `data/build/java.so` on first use.

## 3. Test generation with the specification-based approach

1. **Build the source data** with [generate_source_data_for_prompt.ipynb](generate_source_data_for_prompt.ipynb). Set `version = 'buggy'`, run the notebook, then rerun it with `version = 'fixed'` — both outputs are needed. This walks every bug in `data/d4j2_fix_info/`, parses the checked-out projects, and writes `data/prompts/{version}_source_data_draft.jsonl`. The early cells are an optional single-bug walkthrough (hardcoded to `Time_12`); the batch pipeline is the loop near the end of the notebook.
2. **Unify the buggy and fixed datasets** with [unify_fixed_and_buggy_bugs.ipynb](unify_fixed_and_buggy_bugs.ipynb). This filters to public/protected focal methods, keeps only (bug, method) pairs present in both versions, and writes `data/prompts/{version}_source_data_unified*.jsonl`.
3. **Generate specification docstrings.** Set your API key in the first cell (`%env OPENAI_API_KEY=...`) and run:
   - [Docstring_Generation.ipynb](Docstring_Generation.ipynb) for the **basic** docstring prompt, and/or
   - [Advanced_Docstring_Generation.ipynb](Advanced_Docstring_Generation.ipynb) for the **advanced** prompt (critical analysis of logical mistakes and robustness omissions before writing the docstring).

   Set `version` (`'buggy'`/`'fixed'`) and `tgt_model` (a label used in file names). The API model is hardcoded as `model="gpt-4.1"` in the API-call cells — change it there (and the client, if using a non-OpenAI provider) to run other models.
4. **Build the test-generation prompts** with [generate_prompt.ipynb](generate_prompt.ipynb). Set `tgt_model`, `version`, and `file_post_fix` to match step 3 (the `file_post_fix` variants correspond to the prompt ablations: with code, with docstring, with/without chain-of-thought, few-shot examples, minimum test number). Prompts are written to `data/prompts/rq1/`.
5. **Generate the unit tests** with [UT_Test_Generation.ipynb](UT_Test_Generation.ipynb). Set your API key and the same `tgt_model`/`version`/`file_post_fix` as step 4. The API model is hardcoded (`model="o4-mini"` with `reasoning_effort="high"`) in the API-call cells — adjust the model, reasoning settings, and client for the LLM you are evaluating. Output: `data/prompts/rq1/*_with_completion.jsonl`.

## 4. Evaluation

1. **Compile and run the generated tests** with [UT_Compile_and_Test_fixed_project.ipynb](UT_Compile_and_Test_fixed_project.ipynb) (tests generated from fixed code) and [UT_Compile_and_Test_Project.ipynb](UT_Compile_and_Test_Project.ipynb) (tests generated from buggy code). Each generated test class is injected into **both** the fixed and buggy checkouts, compiled with a repair loop, executed with `defects4j test`, and measured with JaCoCo. Outputs:
   - run logs: `data/rq1/logs/`
   - summary metrics (compile/run rates, bug detection, misguidance): `data/rq1/results_test/chatgpt/{version}_gen_test_results.json`
   - `data/prompts/rq1/*_err_msg_with_completion.jsonl` — failed tests with their error messages, used as input for the multi-round refinement experiments (see `Prompt_example/Prompt_for_Refinement`)
2. **Sequence-score analysis** (model-internal preference, RQ1):
   1. Run [organize_seq_score_calc_json.ipynb](organize_seq_score_calc_json.ipynb) to rebuild each generation prompt and pair it with the effective/misguided tests from the evaluation logs, producing `{prefix, responses}` pair JSONs under `data/seq_score_calc/`.
   2. Place the pair JSONs in a `qa_pairs/` directory next to [seq_score_calc.py](seq_score_calc.py) (or edit its input path), then run it. Edit in-file: `model_name` (the vLLM-served scoring model, default `openai/gpt-oss-120b`), `ut_models` (the generation models to score), and `file_postfix`. Results are written to `seq_score_record/` and appended to `final_summary_statistics.txt`.

## Prompt examples

The [Prompt_example](Prompt_example) directory contains complete example prompts for basic docstring generation, advanced docstring generation (base and reasoning model variants), test generation, and the multi-round refinement step.

## Manual inspection results

[section4.4_manual_inspection_results.xlsx](section4.4_manual_inspection_results.xlsx) contains the dual-annotated manual inspection of generated docstrings reported in Section 4.4 of the paper (whether bugs from the code under test are inherited by the generated specifications).

## Citation

This package is permanently archived on Zenodo: [10.5281/zenodo.21428153](https://doi.org/10.5281/zenodo.21428153) (all versions). To cite the paper:

```bibtex
@article{zhao2026misguidance,
  author    = {Zhao, Junda and Zhou, Shurui and Cohen, Eldan},
  title     = {Evaluating and Mitigating the Misguidance Effect of Buggy Code in {LLM}-Generated Unit Tests},
  journal   = {Proceedings of the ACM on Software Engineering},
  volume    = {3},
  number    = {ISSTA},
  articleno = {ISSTA113},
  year      = {2026},
  publisher = {Association for Computing Machinery},
  doi       = {10.1145/3832204}
}
```

## License

This package is released under the [MIT License](LICENSE). Portions adapted from third-party works (LLM4UT, tree-sitter-java, Defects4J) retain their original licenses — see [NOTICE](NOTICE).

## Acknowledgments

- The prompt-construction and evaluation harness is adapted from the LLM4UT artifact of Yang et al., *On the Evaluation of Large Language Models in Unit Test Generation* (ASE 2024).
- Bug data from [Defects4J](https://github.com/rjust/defects4j).
