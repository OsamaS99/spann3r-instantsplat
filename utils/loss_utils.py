#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use 
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@inria.fr
#

import torch
import torch.nn.functional as F
#import pytorch3d
import numpy as np
import open3d as o3d
from torch.autograd import Variable
from math import exp

def l1_loss_mask(network_output, gt, mask):
    # Calculate the absolute difference
    diff = torch.abs(network_output - gt)
    # Apply the mask
    masked_diff = diff * mask
    # Calculate the mean over the non-zero mask elements
    return masked_diff.sum() / mask.sum()

def ssim_loss_mask(img1, img2, mask, window_size=11, size_average=True):
    channel = img1.size(-3)
    window = create_window(window_size, channel)

    if img1.is_cuda:
        window = window.cuda(img1.get_device())
    window = window.type_as(img1)

    # Apply the mask to both images
    img1_masked = img1 * mask
    img2_masked = img2 * mask
    return _ssim(img1_masked, img2_masked, window, window_size, channel, size_average)

def l1_loss(network_output, gt):
    return torch.abs((network_output - gt)).mean()

def l2_loss(network_output, gt):
    return ((network_output - gt) ** 2).mean()

def gaussian(window_size, sigma):
    gauss = torch.Tensor([exp(-(x - window_size // 2) ** 2 / float(2 * sigma ** 2)) for x in range(window_size)])
    return gauss / gauss.sum()


def smooth_loss(disp, img):
    grad_disp_x = torch.abs(disp[:,1:-1, :-2] + disp[:,1:-1,2:] - 2 * disp[:,1:-1,1:-1])
    grad_disp_y = torch.abs(disp[:,:-2, 1:-1] + disp[:,2:,1:-1] - 2 * disp[:,1:-1,1:-1])
    grad_img_x = torch.mean(torch.abs(img[:, 1:-1, :-2] - img[:, 1:-1, 2:]), 0, keepdim=True) * 0.5
    grad_img_y = torch.mean(torch.abs(img[:, :-2, 1:-1] - img[:, 2:, 1:-1]), 0, keepdim=True) * 0.5
    grad_disp_x *= torch.exp(-grad_img_x)
    grad_disp_y *= torch.exp(-grad_img_y)
    return grad_disp_x.mean() + grad_disp_y.mean()

def create_window(window_size, channel):
    _1D_window = gaussian(window_size, 1.5).unsqueeze(1)
    _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
    window = Variable(_2D_window.expand(channel, 1, window_size, window_size).contiguous())
    return window

def ssim(img1, img2, window_size=11, size_average=True):
    channel = img1.size(-3)
    window = create_window(window_size, channel)

    if img1.is_cuda:
        window = window.cuda(img1.get_device())
    window = window.type_as(img1)

    return _ssim(img1, img2, window, window_size, channel, size_average)

def _ssim(img1, img2, window, window_size, channel, size_average=True):
    mu1 = F.conv2d(img1, window, padding=window_size // 2, groups=channel)
    mu2 = F.conv2d(img2, window, padding=window_size // 2, groups=channel)

    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2

    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size // 2, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size // 2, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size // 2, groups=channel) - mu1_mu2

    C1 = 0.01 ** 2
    C2 = 0.03 ** 2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

    if size_average:
        return ssim_map.mean()
    else:
        return ssim_map.mean(1).mean(1).mean(1)

def load_point_cloud(file_path):
    """
    Load the point cloud as a FloatTensor.
    """
    pcd = o3d.io.read_point_cloud(file_path)
    return torch.tensor(np.asarray(pcd.points), dtype=torch.float32)

def load_mesh_as_pointcloud(file_path, num_samples=2000):
    """
    Loads the mesh and randomly samples (num_samples) points from its surface.
    """
    mesh = o3d.io.read_triangle_mesh(file_path)

    if not mesh.has_vertex_normals(): 
        mesh.compute_vertex_normals()

    pcd = mesh.sample_points_uniformly(number_of_points=num_samples)

    return torch.tensor(np.asarray(pcd.points), dtype=torch.float32)

def chamfer_loss(pc_path1, pc_path2): 
    pc1 = load_point_cloud(pc_path1).unsqueeze(0)  # batch dimension
    pc2 = load_point_cloud(pc_path2).unsqueeze(0)

    return 0
    #return pytorch3d.loss.chamfer_distance(pc1, pc2)

def mesh_chamfer_loss(mesh_path1, mesh_path2): 
    pc1 = load_mesh_as_pointcloud(mesh_path1).unsqueeze(0)
    pc2 = load_mesh_as_pointcloud(mesh_path2).unsqueeze(0)

    return 0
    # return pytorch3d.loss.chamfer_distance(pc1, pc2)