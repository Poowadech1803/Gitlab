def analyze_dc(voltage_v, resistance_ohm):
    if resistance_ohm == 0:
        raise ValueError("Resistance must not be zero.")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


def main():
    try:
        voltage_v = float(input("Enter voltage (V): "))
        resistance_ohm = float(input("Enter resistance (ohm): "))
    except ValueError:
        print("Please enter valid numbers.")
        return

    try:
        result = analyze_dc(voltage_v, resistance_ohm)
    except ValueError as error:
        print(error)
        return

    print(f"Current: {result['current_a']:.2f} A")
    print(f"Power: {result['power_w']:.2f} W")


if __name__ == "__main__":
    main()