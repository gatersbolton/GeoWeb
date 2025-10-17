function [strike, dip] = stress_vector_to_strike_dip(sv)
    % Convert a stress vector (sv = [x; y; z]) to strike and dip.
    
    % Calculate phi (in degrees)
    phi = atan(abs(sv(2) / (sv(1) + 1e-6)));
    phi = rad2deg(phi);
    
    % Determine the strike based on the quadrant.
    if sv(2) >= 0 && sv(1) >= 0
        strike = phi;
    elseif sv(2) >= 0 && sv(1) < 0
        strike = 180 - phi;
    elseif sv(2) < 0 && sv(1) < 0
        strike = 180 + phi;
    elseif sv(2) < 0 && sv(1) >= 0
        strike = 360 - phi;
    end

    % Calculate dip.
    theta = acos(abs(sv(3)));
    dip = 90 - rad2deg(theta);
    
    % If dip is 90, then strike is set to 0.
    if dip == 90
        strike = 0;
    end
end
