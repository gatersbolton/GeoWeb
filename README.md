整体来看，AIFracPick_code/fracseg_unet2d_tensorflow/ 目录下包含两条主要流程：

训练脚本 train.py

推理／裂隙识别脚本 pred.py

下面分别说明它们各自的输入与输出。

------

一、train.py（模型训练）

------

主要输入

- 训练集：input_path_train 与 label_path_train 两个文件夹

- 每个样本存成 0.npy, 1.npy … 等 2-D NumPy 数组

- 输入文件夹放原始图像（尺寸默认 256×256，灰度 1 通道）

- 标签文件夹放对应的二值裂隙掩膜（同尺寸）

- 验证集：input_path_valid 与 label_path_valid，格式同上

- 其它参数

- params：批量大小、样本尺寸、通道数、是否 shuffle

- n_epoch：训练轮数

- checkpoint_path：权重与曲线保存位置

主要输出

- 模型权重：checkpoint_path/unet-best.hdf5（在验证集 mIoU 最高处保存）

- 训练过程曲线图：

- history for learning rate.png

- history for metric.png（acc / mIoU）

- history for loss.png

- 终端打印：模型结构、每 epoch 的 loss / acc / IoU、总训练时长

------

二、pred.py（裂隙识别 / 推理）

------

主要输入

- 训练好的模型文件：model_path = .../unet-best.hdf5

- ATV（成像测井）振幅日志 CSV 文件

  Apply to train.py

     input_path = [

  ​     '/path/to/20230220_SB41_ATV_Amplitude_PreFrac.csv',

  ​     ...        # 如有多通道，可再放多个 CSV

     ]

每个 CSV 第一行写单位，第一列为测深，后续列为 0-360° 各方位振幅。

- 其它参数

- sample_size (256×256)：对原始日志按深度分块裁剪的尺寸

- batch_size：推理批量

- bthres：概率转语义分割时的二值化阈值

- diam、azimin：用于几何计算（井径、最小方位覆盖度）

- output_dir：所有结果保存目录

主要输出（全部保存在 output_dir）

文件名 | 含义

fracture_probability.csv | 每个像素的裂隙概率（0-1 浮点）

fracture_segmentation_threshold0.5.csv | 语义分割 0/1（二值掩膜）

fracture_instance.csv | 实例分割标号（1,2,3…）

fracture_skeleton.csv | 每条裂隙的骨架像素

fracture_geometry.csv | 表格：裂隙中心深度 Depth、倾角 Dip、走向方位 Dip azimuth

终端还会输出加载进度、批推理进度及 “All done!” 提示。

推理流程概要

① 读取 CSV → 裁剪成若干 256×256 patch；② 逐批送入 U-Net 预测概率；

③ 概率图 > 二值化（阈值 0.5）→ 获得语义分割；

④ 连通域标号 → 获得实例分割；⑤ 对每个实例骨架拟合正弦曲线，计算倾角与方位；

⑥ 将概率、语义／实例掩膜、骨架与几何参数按 CSV 保存。

------

总结

------

• 训练阶段：输入为 .npy 形式的图像＋标签，输出为模型权重及训练曲线。

- 推理阶段：输入为 ATV 振幅日志 CSV，输出为多种 CSV：概率图、语义掩膜、实例掩膜、骨架以及裂隙几何表。
