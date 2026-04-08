import matplotlib.pyplot as plt


def PlotLanchester(data):
    """
    Generates a casualty chart for both armies to visualize Lanchester's Law.

    This function processes simulation results to compare how different 
    unit archetypes perform as the initial army size (N) increases. 
    It specifically plots the number of casualties (losses) for Army 2.

    Args:
        data (dict): A dictionary where keys are tuples of (unit_type, N) 
                    and values are the number of surviving units from Army 2.

    Visualization:
        - X-axis: The base unit count (N).
        - Y-axis: Total casualties (calculated as Initial 2N - Survivors).
        - Legend: Differentiates results by unit type (e.g., Knight, Archer).
    """

    # Data organization per unit type
    results = {}

    for (unit_type, N), surv2 in data.items():
        if unit_type not in results:
            results[unit_type] = {"N": [], "army2": []}

        results[unit_type]["N"].append(N)
        results[unit_type]["army2"].append((2 * N) - surv2)

    # Curve for each unit type
    for unit_type, vals in results.items():
        N = vals["N"]
        y2 = vals["army2"]

        plt.plot(N, y2, label=f"{unit_type} - Army 2 (2N)", linestyle="solid")

    plt.xlabel("N (base number of units)")
    plt.ylabel("Casualties")
    plt.title("Lanchester's Law Simulation Results")
    plt.legend()
    plt.grid(True)
    plt.show()
