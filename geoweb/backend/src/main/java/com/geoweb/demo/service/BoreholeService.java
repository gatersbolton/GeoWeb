package com.geoweb.demo.service;

import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

public interface BoreholeService {
    // 新的两步处理方法
    Map<String, Object> calculateBoreholeEllipticity(
        MultipartFile ttFile, 
        MultipartFile wttFile, 
        MultipartFile maskFile,
        Double rp, 
        Double vf, 
        Double wtt, 
        Double beta,
        String useDemo);
    
    Map<String, Object> visualizeBoreholeEllipticity(
        String sessionId,
        MultipartFile ampFile,
        MultipartFile incFile,
        MultipartFile aziFile,
        Double dz,
        Double lenZ,
        String cmapAmp,
        String cmapRad,
        String useVizDemo,
        Double zTop,
        Double zCenter,
        String quality);
    
    // 保留旧方法以确保兼容性
    Map<String, Object> processBoreholeEllipticity(
        MultipartFile ttFile, 
        MultipartFile wttFile, 
        MultipartFile maskFile,
        Double rp, 
        Double vf, 
        Double wtt, 
        Double beta);
} 