#SIMULATION (Map URL)
## The core idea: Trees reduce temperature. We model this as a function of NDBI (urban-ness) and a user-defined tree increase factor.
## The formula is: cooling_effect = NDBI * 10 * tree_increase (clamped to reasonable limits)  
cooling_efficiency = ndbi_raw.multiply(10).add(5).clamp(2, 15)
cooling_map = cooling_efficiency.multiply(float(tree_increase)) # The user-defined tree increase factor (e.g., 0.1 for 10% more trees)
simulated_lst = lst_raw.subtract(cooling_map) # The new simulated LST after adding trees
