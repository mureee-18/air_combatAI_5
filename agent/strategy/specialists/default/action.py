def nearest_turn_index(desired_az, num_turn):
    az = (desired_az + 180.0) % 360.0 - 180.0
    step = 360.0 / num_turn
    return int(round((az + 180.0) / step)) % num_turn
