import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value, PULP_CBC_CMD
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class CostParams:
    c_reg: float
    c_ot: float
    c_rm: float
    c_sub: float
    c_hire: float
    c_fire: float
    c_inv: float
    c_short: float

@dataclass
class CapacityParams:
    worker_cap: float
    capacity_max: float
    rm_per_unit: float

@dataclass
class InitialConditions:
    i0: float
    i0_rm: float
    w0: float

@dataclass
class SupplyParams:
    rm_arrival: List[float]

@dataclass
class DemandScenario:
    name: str
    demand: List[float]
    probability: float

def solve_single_scenario(demand: List[float], cost: CostParams, cap: CapacityParams, 
                          init: InitialConditions, sup: SupplyParams, strategy: str) -> Tuple[List[dict], float, int]:
    T = len(demand)
    prob = LpProblem("Aggregate_Planning", LpMinimize)
    
    # 1. Definisi Variabel
    P = [LpVariable(f"P_{t}", lowBound=0, upBound=cap.capacity_max) for t in range(T)]
    W = [LpVariable(f"W_{t}", lowBound=0) for t in range(T)]
    H = [LpVariable(f"H_{t}", lowBound=0) for t in range(T)]
    F = [LpVariable(f"F_{t}", lowBound=0) for t in range(T)]
    OT = [LpVariable(f"OT_{t}", lowBound=0) for t in range(T)]
    SC = [LpVariable(f"SC_{t}", lowBound=0) for t in range(T)]
    I = [LpVariable(f"I_{t}", lowBound=0) for t in range(T)]
    SO = [LpVariable(f"SO_{t}", lowBound=0) for t in range(T)]
    RM_Inv = [LpVariable(f"RM_Inv_{t}", lowBound=0) for t in range(T)]

    # 2. Fungsi Objektif (Minimasi Biaya)
    prob += lpSum([
        cost.c_reg * P[t] + cost.c_ot * OT[t] + cost.c_rm * P[t] * cap.rm_per_unit +
        cost.c_sub * SC[t] + cost.c_hire * H[t] + cost.c_fire * F[t] +
        cost.c_inv * I[t] + cost.c_short * SO[t]
        for t in range(T)
    ])

    # 3. Kendala (Constraints)
    for t in range(T):
        # Keseimbangan Barang Jadi
        prev_I = init.i0 if t == 0 else I[t-1]
        prob += prev_I + P[t] + SC[t] + OT[t] - demand[t] == I[t] - SO[t]
        
        # Keseimbangan Pekerja
        prev_W = init.w0 if t == 0 else W[t-1]
        prob += W[t] == prev_W + H[t] - F[t]
        
        # Batas Kapasitas Pekerja
        prob += P[t] <= W[t] * cap.worker_cap
        
        # Keseimbangan Bahan Baku (Sudah direvisi)
        prev_RM = init.i0_rm if t == 0 else RM_Inv[t-1]
        prob += RM_Inv[t] == prev_RM + sup.rm_arrival[t] - (P[t] * cap.rm_per_unit)

    # 4. Kendala Strategi Produksi
    if strategy == "level":
        for t in range(1, T):
            prob += P[t] == P[t-1]  # Produksi stabil
    elif strategy == "chase":
        for t in range(T):
            prob += P[t] + SC[t] + OT[t] == demand[t]  # Produksi ketat ikuti demand

    # 5. Jalankan Solver
    prob.solve(PULP_CBC_CMD(msg=0))
    
    # Ekstraksi nilai yang aman (menghindari error NoneType)
    def get_val(var):
        v = value(var)
        return float(max(0.0, v)) if v is not None else 0.0

    plan = []
    total_cost = value(prob.objective) if value(prob.objective) is not None else 0.0
    
    for t in range(T):
        plan.append({
            "Period": t + 1,
            "Demand": demand[t],
            "Production": get_val(P[t]),
            "Workers": get_val(W[t]),
            "Hired": get_val(H[t]),
            "Fired": get_val(F[t]),
            "Overtime": get_val(OT[t]),
            "Subcontract": get_val(SC[t]),
            "Inventory": get_val(I[t]),
            "Shortage": get_val(SO[t]),
            "RM_Inventory": get_val(RM_Inv[t])
        })
        
    return plan, total_cost, prob.status

def solve_all_scenarios(scenarios: List[DemandScenario], cost: CostParams, cap: CapacityParams, 
                        init: InitialConditions, sup: SupplyParams, strategy: str):
    all_plans = []
    cost_summary = []
    
    for scen in scenarios:
        plan, total_cost, status = solve_single_scenario(scen.demand, cost, cap, init, sup, strategy)
        df = pd.DataFrame(plan)
        df.insert(0, "Scenario", scen.name)
        all_plans.append(df)
        
        cost_summary.append({
            "Scenario": scen.name,
            "Probability": scen.probability,
            "Total Cost": total_cost,
            "Expected Cost": total_cost * scen.probability
        })
        
    df_plans = pd.concat(all_plans, ignore_index=True)
    df_costs = pd.DataFrame(cost_summary)
    
    return df_plans, df_costs