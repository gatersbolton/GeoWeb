function [theta_major, theta_minor] = EllipAxisOrien(phi, ...
                                                     S3, ...
                                                     EulerAngles, ...
                                                     Borehole_Tilt, ...
                                                     Borehole_Azimuth)
%% 正演任意倾斜钻孔发生弹性形变后，钻孔横截面长、短轴的方位角。

% 输入变量:
% phi: 应力比，(S2 - S3) / (S1 - S3)
% S3: 最小主应力相对大小（0-1）
% EulerAngles：主应力坐标系与地理坐标系的欧拉角
% Borehole_Tilt：钻孔倾斜角
% Borehole_Azimuth：钻孔倾斜方位角

% 输出变量：
% theta_minor：钻孔横截面短轴方位角
% theta_major：钻孔横截面长轴方位角

%% Define principal stress tensor
S1 = 1; 
S2 = (1-S3)*phi+S3;
S = zeros(3,3);
S(1,1) = S1;
S(2,2) = S2;
S(3,3) = S3;

%% Transformation matrices
% Far-filed stress -> geographic
EulerAngles = deg2rad(EulerAngles);
a = EulerAngles(1); b = EulerAngles(2); c = EulerAngles(3);
Rs = [cos(a)*cos(b) sin(a)*cos(b) -sin(b);...
      cos(a)*sin(b)*sin(c)-sin(a)*cos(c) sin(a)*sin(b)*sin(c)+cos(a)*cos(c) cos(b)*sin(c);...
      cos(a)*sin(b)*cos(c)+sin(a)*sin(c) sin(a)*sin(b)*cos(c)-cos(a)*sin(c) cos(b)*cos(c);];

% Geographic -> borehole
alpha = deg2rad(Borehole_Tilt);
delta = deg2rad(Borehole_Azimuth);
Rb = [cos(alpha)*cos(delta) cos(alpha)*sin(delta) -sin(alpha);...
      -sin(delta) cos(delta) 0;...
      sin(alpha)*cos(delta) sin(alpha)*sin(delta) cos(alpha);];

% Tensor transformation     
sigma = Rb*Rs'*S*Rs*Rb';
sigma(abs(sigma)<1e-5) = 0;

%% Major and minor axis azimuth from high side
theta_axis = atan(2 * sigma(1,2) / abs(sigma(1,1) - sigma(2,2))) / 2;
theta_axis = rad2deg(theta_axis);

if sigma(1,1) < sigma(2,2)
    theta_major = Borehole_Azimuth - theta_axis;
    if theta_major > 360
        theta_major = theta_major - 360;
    end
    if theta_major < 0
        theta_major = theta_major + 360;
    end
    theta_minor = theta_major + 90;
    if theta_minor > 360
        theta_minor = theta_minor - 360;
    end
    if theta_minor < 0
        theta_minor = theta_minor + 360;
    end
end

if sigma(1,1) > sigma(2,2)
    theta_minor = Borehole_Azimuth + theta_axis;
    if theta_minor > 360
        theta_minor = theta_minor - 360;
    end
    if theta_minor < 0
        theta_minor = theta_minor + 360;
    end
    theta_major = theta_minor + 90;
    if theta_major > 360
        theta_major = theta_major - 360;
    end
    if theta_major < 0
        theta_major = theta_major + 360;
    end
end

if sigma(1,1) == sigma(2,2)
    theta_major = NaN;
    theta_minor = NaN;
end

end