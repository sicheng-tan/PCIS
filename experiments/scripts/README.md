# Ablation launch scripts (CVC5, full706, skip → 686)

| Paper | Script | Config |
|-------|--------|--------|
| **PCR** | `run_ablation_pcr.sh` | `experiments/configs/ablation_pcr.env` |
| **GSE** | `run_ablation_gse.sh` | `experiments/configs/ablation_gse.env` |
| **PCIS** | `run_ablation_pcis.sh` | `experiments/configs/ablation_pcis.env` |

## Prep

```bash
cd /path/to/PCIS
cp experiments/configs/ablation_pcr.env.example experiments/configs/ablation_pcr.env
cp experiments/configs/ablation_gse.env.example experiments/configs/ablation_gse.env
cp experiments/configs/ablation_pcis.env.example experiments/configs/ablation_pcis.env
# fill OPENAI_API_KEY / OPENAI_API_BASE / OPENAI_MODEL in each .env
```

## Run

```bash
bash experiments/scripts/run_ablation_pcr.sh
bash experiments/scripts/run_ablation_gse.sh
bash experiments/scripts/run_ablation_pcis.sh
```

Optional overrides: `DOTENV_PATH`, `RESULT_DIR`, `SKIP_FILE`.

Default results go to `experiments/results/ablation_{pcr,gse,pcis}/`.
Each chain runs `autoproof` → `dtt` → `ind-ben` → `vmcai15-dt` under `nohup`.

Optional shared knobs (not ablation-specific): `cp experiments/configs/shared.env.example experiments/configs/shared.env`
