function [aphi, stress_regime] = compute_aphi(phi, s1_dip, s2_dip, s3_dip)
% COMPUTE_APHI computes the aphi value and stress regime based on input
% phi and stress dip angles.
%
% Inputs:
%   phi    - scalar or vector (in arbitrary units)
%   s1_dip - scalar or vector corresponding to S1 dip
%   s2_dip - scalar or vector corresponding to S2 dip
%   s3_dip - scalar or vector corresponding to S3 dip
%
% Outputs:
%   aphi         - computed aphi value(s)
%   stress_regime- string or cell array of strings indicating the stress regime.
%
% The stress regimes are determined as follows:
%   - 'Normal' for (s1_dip > s2_dip >= s3_dip) or (s1_dip > s3_dip >= s2_dip)
%   - 'Strike-slip' for (s2_dip > s1_dip >= s3_dip) or (s2_dip > s3_dip >= s1_dip)
%   - 'Reverse' for (s3_dip > s2_dip >= s1_dip) or (s3_dip > s1_dip >= s2_dip)

    % If phi is a scalar, convert inputs to column vectors.
    if isscalar(phi)
        phi    = phi(:);
        s1_dip = s1_dip(:);
        s2_dip = s2_dip(:);
        s3_dip = s3_dip(:);
    elseif ~isnumeric(phi)
        error('Input parameters must be numeric (scalar or array).');
    end

    npts = numel(phi);
    aphi = zeros(npts, 1);
    stress_regime = cell(npts, 1);

    % Loop over each element
    for i = 1:npts
        % Check Normal faulting stress regime.
        if ( (s1_dip(i) > s2_dip(i) && s2_dip(i) >= s3_dip(i)) || ...
             (s1_dip(i) > s3_dip(i) && s3_dip(i) >= s2_dip(i)) )
            n = 0;
            stress_regime{i} = 'Normal';
        end

        % Check Strike-slip faulting stress regime.
        if ( (s2_dip(i) > s1_dip(i) && s1_dip(i) >= s3_dip(i)) || ...
             (s2_dip(i) > s3_dip(i) && s3_dip(i) >= s1_dip(i)) )
            n = 1;
            stress_regime{i} = 'Strike-slip';
        end

        % Check Reverse faulting stress regime.
        if ( (s3_dip(i) > s2_dip(i) && s2_dip(i) >= s1_dip(i)) || ...
             (s3_dip(i) > s1_dip(i) && s1_dip(i) >= s2_dip(i)) )
            n = 2;
            stress_regime{i} = 'Reverse';
        end

        % Compute aphi for this index.
        aphi(i) = (n + 0.5) + (-1)^n * (phi(i) - 0.5);
    end

    % If there is only one element, convert outputs from vector/cell to scalar/string.
    if numel(aphi) == 1
        aphi = aphi(1);
    end
    if numel(stress_regime) == 1
        stress_regime = stress_regime{1};
    end
end
