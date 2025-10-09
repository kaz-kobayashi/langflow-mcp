# Unimplemented Features Analysis Report
**Jupyter Notebook**: `/Users/kazuhiro/Documents/2510/langflow-mcp/nbs/03inventory.ipynb`
**Date**: 2025-10-09

## Executive Summary

Total functions in notebook: **35**
Functions in optinv.py: **35** (1 missing: `forecast`)
Functions exposed via MCP: **32**
**Core functions not exposed as MCP tools: 15**

### Implementation Status
- ✅ All core inventory optimization functions are in `optinv.py`
- ✅ Most functions are exposed via MCP tools with wrappers
- ⚠️ `forecast` function exists in notebook but NOT in `optinv.py` (wrapped in `forecast_utils.py`)
- ⚠️ 15 functions exist but are NOT exposed as MCP tools

---

## 1. Functions in Notebook but NOT in optinv.py

### 1.1 forecast (HIGH PRIORITY - MISSING)
- **Status**: NOT in optinv.py
- **Location**: Wrapped in `forecast_utils.py` as `forecast_demand`
- **Description**: Prophet-based demand forecasting with confidence intervals
- **Impact**: High - Core forecasting functionality
- **Recommendation**: Add `forecast` function to `optinv.py` or document that it's intentionally in `forecast_utils.py`

---

## 2. Functions NOT Exposed as MCP Tools (But in optinv.py)

These functions exist in the codebase but users cannot access them via the web app:

### 2.1 Core Simulation Functions

#### base_stock_simulation_using_dist (MEDIUM PRIORITY)
- **Function**: `base_stock_simulation_using_dist`
- **Location**: `scmopt2/optinv.py` line 855
- **Description**: Base stock simulation using distribution-based demand (alternative to fixed demand array)
- **Current Status**: Function exists but no MCP wrapper
- **Priority**: Medium - Useful for advanced simulations
- **Recommendation**: Add MCP tool `simulate_base_stock_with_distribution`

#### network_base_stock_simulation (HIGH PRIORITY)
- **Function**: `network_base_stock_simulation`
- **Location**: `scmopt2/optinv.py` line 986
- **Description**: Multi-echelon network base stock simulation with echelon lead times
- **Current Status**: Used internally by `periodic_inv_opt` but not directly exposed
- **Priority**: High - Core network simulation capability
- **Recommendation**: Add MCP tool `simulate_network_base_stock`

### 2.2 SSA (Safety Stock Allocation) Helper Functions

#### max_demand_compute (LOW PRIORITY)
- **Function**: `max_demand_compute`
- **Location**: `scmopt2/optinv.py` line 1212
- **Description**: Computes maximum demand for SSA optimization
- **Current Status**: Helper function for `dynamic_programming_for_SSA`
- **Priority**: Low - Internal helper function
- **Recommendation**: Keep internal, not needed as MCP tool

#### dynamic_programming_for_SSA (MEDIUM PRIORITY)
- **Function**: `dynamic_programming_for_SSA`
- **Location**: `scmopt2/optinv.py` line 1249
- **Description**: Dynamic programming algorithm for Safety Stock Allocation
- **Current Status**: Alternative optimization method to tabu search
- **Priority**: Medium - Provides exact solution for smaller problems
- **Recommendation**: Add MCP tool `optimize_safety_stock_dp` as alternative to tabu search

### 2.3 Data I/O Functions

#### read_willems (LOW PRIORITY)
- **Function**: `read_willems`
- **Location**: `scmopt2/optinv.py` line 1571
- **Description**: Reads Willems' benchmark data from CSV
- **Current Status**: Helper function for loading test data
- **Priority**: Low - Specific to research benchmarks
- **Recommendation**: Keep internal or add as `load_benchmark_data`

#### extract_data_for_SSA (LOW PRIORITY)
- **Function**: `extract_data_for_SSA`
- **Location**: `scmopt2/optinv.py` line 1595
- **Description**: Extracts SSA parameters from NetworkX graph
- **Current Status**: Data preparation helper
- **Priority**: Low - Internal helper
- **Recommendation**: Keep internal

### 2.4 Visualization Functions

#### draw_graph_for_SSA (LOW PRIORITY)
- **Function**: `draw_graph_for_SSA`
- **Location**: `scmopt2/optinv.py` line 1642
- **Description**: Draws safety stock network using matplotlib
- **Current Status**: Replaced by `visualize_safety_stock_network` (Plotly version in `network_visualizer.py`)
- **Priority**: Low - Superseded by better implementation
- **Recommendation**: Keep for backward compatibility, no MCP tool needed

#### draw_graph_for_SSA_from_df (LOW PRIORITY)
- **Function**: `draw_graph_for_SSA_from_df`
- **Location**: `scmopt2/optinv.py` line 1754
- **Description**: Draws SSA graph from DataFrame input
- **Current Status**: Alternative matplotlib visualization
- **Priority**: Low - Superseded
- **Recommendation**: No action needed

#### plot_inv_opt_lr_find (MEDIUM PRIORITY)
- **Function**: `plot_inv_opt_lr_find`
- **Location**: `scmopt2/optinv.py` line 2102
- **Description**: Plots learning rate finder results for optimization
- **Current Status**: Wrapped in `lr_finder.py` as `visualize_lr_search`
- **Priority**: Medium - Already wrapped
- **Recommendation**: ✅ Already implemented via `find_optimal_learning_rate_periodic`

#### plot_inv_opt (MEDIUM PRIORITY)
- **Function**: `plot_inv_opt`
- **Location**: `scmopt2/optinv.py` line 2124
- **Description**: Plots optimization convergence curve
- **Current Status**: Wrapped in `lr_finder.py` as `visualize_training_progress`
- **Priority**: Medium - Already wrapped
- **Recommendation**: ✅ Already implemented via `visualize_periodic_optimization`

#### plot_simulation (MEDIUM PRIORITY)
- **Function**: `plot_simulation`
- **Location**: `scmopt2/optinv.py` line 2143
- **Description**: Plots inventory simulation trajectories over time
- **Current Status**: Not exposed as MCP tool
- **Priority**: Medium - Useful for result visualization
- **Recommendation**: Add MCP tool `visualize_simulation_trajectories`

### 2.5 Optimization Wrapper Functions

#### make_df_for_SSA (LOW PRIORITY)
- **Function**: `make_df_for_SSA`
- **Location**: `scmopt2/optinv.py` line 1708
- **Description**: Creates DataFrames for SSA optimization from graph
- **Current Status**: Helper function
- **Priority**: Low - Internal data transformation
- **Recommendation**: Keep internal

#### solve_SSA (MEDIUM PRIORITY)
- **Function**: `solve_SSA`
- **Location**: `scmopt2/optinv.py` line 1830
- **Description**: High-level SSA solver (wraps tabu_search_for_SSA)
- **Current Status**: Wrapped by `optimize_safety_stock_allocation`
- **Priority**: Medium - Already wrapped
- **Recommendation**: ✅ Already implemented

---

## 3. Summary of Recommendations

### HIGH PRIORITY (Implement These)

1. **Add `forecast` to optinv.py** or document the separation
   - Current: Only in `forecast_utils.py`
   - Action: Move to optinv.py for consistency OR add note in documentation

2. **Expose `network_base_stock_simulation` as MCP tool**
   - Function: Direct access to multi-echelon simulation
   - Tool name: `simulate_network_base_stock`
   - Use case: Advanced users wanting granular network simulation control

### MEDIUM PRIORITY (Consider Adding)

3. **Expose `dynamic_programming_for_SSA` as MCP tool**
   - Function: Alternative exact optimization for SSA
   - Tool name: `optimize_safety_stock_dp`
   - Use case: Smaller problems needing exact solutions

4. **Expose `plot_simulation` as MCP tool**
   - Function: Visualize inventory trajectories
   - Tool name: `visualize_simulation_trajectories`
   - Use case: Detailed analysis of simulation results

5. **Expose `base_stock_simulation_using_dist` as MCP tool**
   - Function: Simulation with distributional demand
   - Tool name: `simulate_base_stock_with_distribution`
   - Use case: Alternative to fixed demand arrays

### LOW PRIORITY (Optional)

6. Keep internal helper functions internal:
   - `max_demand_compute`
   - `extract_data_for_SSA`
   - `make_df_for_SSA`
   - `read_willems`
   - `draw_graph_for_SSA` (superseded by Plotly version)
   - `draw_graph_for_SSA_from_df`

---

## 4. Already Implemented (Phase 9, 10, 11)

The following were mentioned as implemented and confirmed:

### Phase 9: EOQ Extensions ✅
- `calculate_eoq` ✅
- `calculate_eoq_incremental_discount` ✅
- `calculate_eoq_all_units_discount` ✅
- `visualize_eoq` ✅

### Phase 10: Learning Rate Finder ✅
- `find_optimal_learning_rate_periodic` ✅
- `optimize_periodic_with_one_cycle` ✅
- Wrapped from `lr_finder.py`

### Phase 11: Enhanced Visualizations ✅
- `visualize_safety_stock_network` ✅ (Phase 11-1)
- `fit_histogram_distribution` ✅ (Phase 11-2)
- `simulate_multistage_inventory` ✅ (Phase 11-3)

---

## 5. Implementation Priority Order

Based on user value and implementation complexity:

### Immediate (Week 1)
1. ✅ Document that `forecast` is intentionally in `forecast_utils.py` OR move it to `optinv.py`

### Short-term (Week 2-3)
2. Add `simulate_network_base_stock` MCP tool
3. Add `visualize_simulation_trajectories` MCP tool

### Medium-term (Month 2)
4. Add `optimize_safety_stock_dp` MCP tool (DP alternative)
5. Add `simulate_base_stock_with_distribution` MCP tool

### Long-term (Optional)
6. Consider adding `read_willems` as `load_benchmark_data` for research users

---

## 6. Function Coverage Matrix

| Function | In Notebook | In optinv.py | In MCP | Priority | Action |
|----------|-------------|--------------|---------|----------|--------|
| forecast | ✅ | ❌ | ✅ (wrapped) | HIGH | Document/Move |
| network_base_stock_simulation | ✅ | ✅ | ❌ | HIGH | Add MCP |
| dynamic_programming_for_SSA | ✅ | ✅ | ❌ | MEDIUM | Add MCP |
| plot_simulation | ✅ | ✅ | ❌ | MEDIUM | Add MCP |
| base_stock_simulation_using_dist | ✅ | ✅ | ❌ | MEDIUM | Add MCP |
| max_demand_compute | ✅ | ✅ | ❌ | LOW | Keep internal |
| read_willems | ✅ | ✅ | ❌ | LOW | Keep internal |
| extract_data_for_SSA | ✅ | ✅ | ❌ | LOW | Keep internal |
| make_df_for_SSA | ✅ | ✅ | ❌ | LOW | Keep internal |
| draw_graph_for_SSA | ✅ | ✅ | ❌ | LOW | Superseded |
| draw_graph_for_SSA_from_df | ✅ | ✅ | ❌ | LOW | Superseded |
| plot_inv_opt_lr_find | ✅ | ✅ | ✅ (wrapped) | - | ✅ Done |
| plot_inv_opt | ✅ | ✅ | ✅ (wrapped) | - | ✅ Done |
| solve_SSA | ✅ | ✅ | ✅ (wrapped) | - | ✅ Done |
| multi_stage_simulate_inventory | ✅ | ✅ | ✅ (wrapped) | - | ✅ Done |

---

## Conclusion

The implementation is **highly complete** with 35 functions from the notebook successfully ported to the codebase. The main gaps are:

1. **One function missing from optinv.py**: `forecast` (but it's in `forecast_utils.py`)
2. **15 functions not exposed as MCP tools**, but most are:
   - Internal helpers (LOW priority)
   - Already wrapped in helper modules (✅ DONE)
   - Advanced features that could be added (MEDIUM-HIGH priority)

**Recommended immediate action**: Add 2-3 HIGH/MEDIUM priority MCP tools to provide users with more advanced simulation and optimization capabilities.
