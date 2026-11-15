# Third-party notices

## τ²-bench (retail domain)

From [sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench), commit
`5bfa7e37b36656b37dc6d022156be6563c1007f3`:

- **Copied unmodified:** `data/db.json`, `data/policy.md` and `data/tasks.json`
  (from `data/tau2/domains/retail/`).
- **Copied word for word:** the agent's instruction, system-prompt layout and first message in
  `agent/baseline/agent.py` (from `src/tau2/agent/llm_agent.py`); the tool names, arguments and
  descriptions in `agent/baseline/tools.py` (from `src/tau2/domains/retail/tools.py`); and the
  user-simulation guidelines and scenario layout in `agent/evaluation/simulated_customer.py`
  (from `data/tau2/user_simulator/simulation_guidelines.md` and `src/tau2/data_model/tasks.py`).
- **Adapted:** `agent/store/schema.py` (from `src/tau2/domains/retail/data_model.py`) and
  `agent/store/retail_store.py` (from `src/tau2/domains/retail/tools.py`). The changes are listed
  at the top of each file.

Copyright (c) 2025 Sierra Research, MIT License. The full license text is in
[`data/LICENSE.tau2-bench`](data/LICENSE.tau2-bench).
