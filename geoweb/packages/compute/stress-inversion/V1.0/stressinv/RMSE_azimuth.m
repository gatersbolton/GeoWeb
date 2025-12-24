function rmse = RMSE_azimuth(x, y)
% function rmse = circular_rmse(x, y)
%
% Compute circular root-mean-square error between x and y.
%
% Inputs:
% x: Size (m, 1) matrix of azimuth between 0° and 360°.
% y: Size (m, 1) matrix of azimuth between 0° and 360°.
%
% Returns:
% rmse: circular root-mean-square error beetween x and y.

% Check input value range.
if any(x < 0) || any(x > 360) || any(y < 0) || any(y > 360)
    error("Input values can not be less than 0 or greater than 360.")
end
% Convert the input azimuth to be between 0° and 180°.
x(x > 180) = x(x > 180) - 180;
y(y > 180) = y(y > 180) - 180;
% Compute circular RMSE.
e = zeros(3, length(x));
e(1, :) = abs(x - y);  % Absolute error 1
e(2, :) = abs(x + 180 - y);  % Absolute error 2.
e(3, :) = abs(y + 180 - x);  % Absolute error 3.
emin = min(e);
rmse = sqrt(mean(emin.^2, 'omitnan'));

end

