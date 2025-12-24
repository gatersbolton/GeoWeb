package com.geoweb.demo.controller;

import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.geoweb.demo.service.BoreholeService;

@RestController
@RequestMapping("/api/borehole")
public class BoreholeController {

    @Autowired
    private BoreholeService boreholeService;

    @PostMapping(value = "/calculate", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> calculateBoreholeEllipticity(
            @RequestPart(value = "tt_file", required = false) MultipartFile ttFile,
            @RequestPart(value = "wtt_file", required = false) MultipartFile wttFile,
            @RequestPart(value = "mask_file", required = false) MultipartFile maskFile,
            @RequestParam("rp") Double rp,
            @RequestParam("vf") Double vf,
            @RequestParam(value = "wtt", required = false) Double wtt,
            @RequestParam(value = "beta", required = false) Double beta,
            @RequestParam(value = "use_demo", required = false) String useDemo) {
        
        return boreholeService.calculateBoreholeEllipticity(
            ttFile, wttFile, maskFile, rp, vf, wtt, beta, useDemo);
    }

    @PostMapping(value = "/visualize", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> visualizeBoreholeEllipticity(
            @RequestParam("session_id") String sessionId,
            @RequestPart(value = "amp_file", required = false) MultipartFile ampFile,
            @RequestPart(value = "inc_file", required = false) MultipartFile incFile,
            @RequestPart(value = "azi_file", required = false) MultipartFile aziFile,
            @RequestParam(value = "dz", required = false) Double dz,
            @RequestParam(value = "lenZ", defaultValue = "5") Double lenZ,
            @RequestParam(value = "cmapAmp", defaultValue = "gray") String cmapAmp,
            @RequestParam(value = "cmapRad", defaultValue = "gray_r") String cmapRad,
            @RequestParam(value = "use_viz_demo", required = false) String useVizDemo,
            @RequestParam(value = "zTop", required = false) Double zTop,
            @RequestParam(value = "zCenter", required = false) Double zCenter,
            @RequestParam(value = "quality", defaultValue = "final") String quality) {

        return boreholeService.visualizeBoreholeEllipticity(
            sessionId, ampFile, incFile, aziFile, dz, lenZ, cmapAmp, cmapRad, useVizDemo, zTop, zCenter, quality);
    }

    // 保留旧的API以确保兼容性
    @PostMapping(value = "/process", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> processBoreholeEllipticity(
            @RequestPart("tt_file") MultipartFile ttFile,
            @RequestPart(value = "wtt_file", required = false) MultipartFile wttFile,
            @RequestPart(value = "mask_file", required = false) MultipartFile maskFile,
            @RequestParam("rp") Double rp,
            @RequestParam("vf") Double vf,
            @RequestParam(value = "wtt", required = false) Double wtt,
            @RequestParam(value = "beta", required = false) Double beta) {
        
        return boreholeService.processBoreholeEllipticity(
            ttFile, wttFile, maskFile, rp, vf, wtt, beta);
    }
} 