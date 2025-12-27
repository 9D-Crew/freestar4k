import datetime as dt
import math
EPOCH = dt.datetime(2000, 1, 6, 18, 14, 0)

def _normalize(v):
    v = v - math.floor(v)
    if v < 0:
        v = v + 1
    return v

def _torad(d):
    return d * math.pi / 180.0

def _get_phase_time(k, phase_selector):
    k = k + phase_selector
    T = k / 1236.85
    JDE = (2451550.09766 + 
           29.530588861 * k + 
           0.00015437 * T**2 - 
           0.000000150 * T**3 + 
           0.00000000073 * T**4)
    M = _torad(2.5534 + 29.10535670 * k - 0.0000014 * T**2 - 0.00000011 * T**3)
    Mprime = _torad(201.5643 + 385.81693528 * k + 0.0107582 * T**2 + 0.00001238 * T**3 - 0.000000058 * T**4)
    F = _torad(160.7108 + 390.67050284 * k - 0.0016118 * T**2 - 0.00000227 * T**3 + 0.000000011 * T**4)
    Omega = _torad(124.7746 - 1.56375588 * k + 0.0020672 * T**2 + 0.00000215 * T**3)
    E = 1 - 0.002516 * T - 0.0000074 * T**2
    correction = 0
    if phase_selector == 0.0: # New Moon
        correction += -0.40720 * math.sin(Mprime)
        correction += 0.17241 * E * math.sin(M)
        correction += 0.01608 * math.sin(2 * Mprime)
        correction += 0.01039 * math.sin(2 * F)
        correction += 0.00739 * E * math.sin(Mprime - M)
        correction += -0.00514 * E * math.sin(Mprime + M)
        correction += 0.00208 * E**2 * math.sin(2 * M)
        correction += -0.00111 * math.sin(Mprime - 2 * F)
        correction += -0.00057 * math.sin(Mprime + 2 * F)
    elif phase_selector == 0.5: # Full Moon
        correction += -0.40614 * math.sin(Mprime)
        correction += 0.17302 * E * math.sin(M)
        correction += 0.01614 * math.sin(2 * Mprime)
        correction += 0.01043 * math.sin(2 * F)
        correction += 0.00734 * E * math.sin(Mprime - M)
        correction += -0.00515 * E * math.sin(Mprime + M)
        correction += 0.00209 * E**2 * math.sin(2 * M)
        correction += -0.00111 * math.sin(Mprime - 2 * F)
        correction += -0.00057 * math.sin(Mprime + 2 * F)
    elif phase_selector in [0.25, 0.75]: # Quarters
        correction += -0.62801 * math.sin(Mprime)
        correction += 0.17172 * E * math.sin(M)
        correction += -0.01183 * E * math.sin(Mprime + M)
        correction += 0.00862 * math.sin(2 * Mprime)
        correction += 0.00804 * math.sin(2 * F)
        correction += 0.00454 * E * math.sin(Mprime - M)
        correction += 0.00204 * E**2 * math.sin(2 * M)
        correction += -0.00180 * math.sin(Mprime - 2 * F)
        correction += -0.00070 * math.sin(Mprime + 2 * F)
        w_sign = 1 if phase_selector == 0.25 else -1
        correction += w_sign * (0.00306 - 0.00038 * E * math.cos(M) + 0.00032 * math.cos(Mprime))
    
    JDE_final = JDE + correction
    jd_unix_offset = 2440587.5
    seconds = (JDE_final - jd_unix_offset) * 86400
    return dt.datetime.utcfromtimestamp(seconds)

def _estimate_k(date):
    year = date.year
    year_frac = (date.timetuple().tm_yday - 1) / 365.25
    k = (year + year_frac - 2000) * 12.3685
    return math.floor(k)

def next_new_moon(after):
    if isinstance(after, dt.date) and not isinstance(after, dt.datetime):
        after = dt.datetime.combine(after, dt.time.min)
    
    k = _estimate_k(after)
    for i in range(5): 
        t = _get_phase_time(k + i, 0.0)
        if t > after:
            return t

def next_full_moon(after):
    if isinstance(after, dt.date) and not isinstance(after, dt.datetime):
        after = dt.datetime.combine(after, dt.time.min)
    
    k = _estimate_k(after)
    for i in range(5):
        t = _get_phase_time(k + i, 0.5)
        if t > after:
            return t

def next_first_quarter_moon(after):
    if isinstance(after, dt.date) and not isinstance(after, dt.datetime):
        after = dt.datetime.combine(after, dt.time.min)
    
    k = _estimate_k(after)
    for i in range(5):
        t = _get_phase_time(k + i, 0.25)
        if t > after:
            return t

def next_last_quarter_moon(after):
    if isinstance(after, dt.date) and not isinstance(after, dt.datetime):
        after = dt.datetime.combine(after, dt.time.min)
    
    k = _estimate_k(after)
    for i in range(5):
        t = _get_phase_time(k + i, 0.75)
        if t > after:
            return t

def localtime(date):
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    local_dt = date.astimezone()
    return local_dt.replace(tzinfo=None)