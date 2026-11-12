# CPU benchmark protocol

Do not compare runs with different agent counts, time steps, scenario parameters or program versions as if equivalent. Record Python, NumPy, CPU/OS, wall-clock duration, warm-up policy and an unambiguous workload. The CLI metadata records runtime and environment; code can be profiled separately using `python -m cProfile -s cumulative -m civitas run ...`. Repository release reports are reference observations from one sandbox, not portable throughput promises.
