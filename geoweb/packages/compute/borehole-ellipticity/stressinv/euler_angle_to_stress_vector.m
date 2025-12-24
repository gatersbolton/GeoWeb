function [sv1, sv2, sv3] = euler_angle_to_stress_vector(a, b, c)
    % Convert Euler angles (in degrees) to stress vectors (S1, S2, S3)
    
    % Convert angles from degrees to radians.
    a = deg2rad(a);
    b = deg2rad(b);
    c = deg2rad(c);
    
    % Define an arbitrary stress tensor.
    S = [1, 0, 0; 
         0, 0, 0; 
         0, 0, -1];
     
    % Construct the transformation matrix R.
    R = [ cos(a)*cos(b),                                  sin(a)*cos(b),                                 -sin(b);
         cos(a)*sin(b)*sin(c)-sin(a)*cos(c),  sin(a)*sin(b)*sin(c)+cos(a)*cos(c),  cos(b)*sin(c);
         cos(a)*sin(b)*cos(c)+sin(a)*sin(c),  sin(a)*sin(b)*cos(c)-cos(a)*sin(c),  cos(b)*cos(c)];
     
    % Transform the stress tensor into the geographic coordinate system.
    Sg = R' * S * R;
    
    % Compute eigenvalues and eigenvectors.
    [V, D] = eig(Sg);
    
    % Sort the eigenvalues in descending order.
    eigVals = diag(D);
    [~, idx] = sort(eigVals, 'descend');
    
    % Extract the stress vectors corresponding to sorted eigenvalues.
    sv1 = V(:, idx(1));  % Vector of S1.
    sv2 = V(:, idx(2));  % Vector of S2.
    sv3 = V(:, idx(3));  % Vector of S3.
end
