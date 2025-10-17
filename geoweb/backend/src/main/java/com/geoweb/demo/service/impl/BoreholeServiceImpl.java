package com.geoweb.demo.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.HashMap;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.geoweb.demo.service.BoreholeService;

@Service
public class BoreholeServiceImpl implements BoreholeService {

    @Value("${python.service.url}")
    private String pythonServiceUrl;

    private final WebClient webClient = WebClient.builder()
            .exchangeStrategies(ExchangeStrategies.builder()
                .codecs(configurer -> configurer
                    .defaultCodecs()
                    .maxInMemorySize(50 * 1024 * 1024)) // 50MB缓冲区
                .build())
            .build();

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public Map<String, Object> calculateBoreholeEllipticity(
            MultipartFile ttFile, 
            MultipartFile wttFile, 
            MultipartFile maskFile,
            Double rp, 
            Double vf, 
            Double wtt, 
            Double beta,
            String useDemo) {
        
        try {
            // 构建multipart请求
            var multipartData = BodyInserters.fromMultipartData("rp", String.valueOf(rp))
                .with("vf", String.valueOf(vf));
            
            // 如果使用演示数据
            if ("true".equals(useDemo)) {
                multipartData = multipartData.with("use_demo", "true");
            } else {
                // 添加文件
                if (ttFile != null) {
                    multipartData = multipartData.with("tt_file", ttFile.getResource());
                }
                if (wttFile != null) {
                    multipartData = multipartData.with("wtt_file", wttFile.getResource());
                }
                if (maskFile != null) {
                    multipartData = multipartData.with("mask_file", maskFile.getResource());
                }
            }
            
            if (wtt != null) {
                multipartData = multipartData.with("wtt", String.valueOf(wtt));
            }
            
            if (beta != null) {
                multipartData = multipartData.with("beta", String.valueOf(beta));
            }

            String response = webClient.post()
                    .uri(pythonServiceUrl + "/borehole/calculate")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(multipartData)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();

            if (response != null) {
                return objectMapper.readValue(response, new TypeReference<Map<String, Object>>() {
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        // fallback
        Map<String, Object> fallback = new HashMap<>();
        fallback.put("error", "计算失败，请检查文件格式和参数设置");
        return fallback;
    }

    @Override
    public Map<String, Object> visualizeBoreholeEllipticity(
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
            String quality) {

        try {
            // 构建multipart请求
            var multipartData = BodyInserters.fromMultipartData("session_id", sessionId)
                .with("lenZ", String.valueOf(lenZ))
                .with("cmapAmp", cmapAmp)
                .with("cmapRad", cmapRad);

            // 添加可选文件
            if (ampFile != null) {
                multipartData = multipartData.with("amp_file", ampFile.getResource());
            }
            if (incFile != null) {
                multipartData = multipartData.with("inc_file", incFile.getResource());
            }
            if (aziFile != null) {
                multipartData = multipartData.with("azi_file", aziFile.getResource());
            }

            if (dz != null) {
                multipartData = multipartData.with("dz", String.valueOf(dz));
            }

            if (useVizDemo != null) {
                multipartData = multipartData.with("use_viz_demo", useVizDemo);
            }
            if (zTop != null) {
                multipartData = multipartData.with("zTop", String.valueOf(zTop));
            }
            if (zCenter != null) {
                multipartData = multipartData.with("zCenter", String.valueOf(zCenter));
            }
            if (quality != null) {
                multipartData = multipartData.with("quality", quality);
            }

            String response = webClient.post()
                    .uri(pythonServiceUrl + "/borehole/visualize")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(multipartData)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();

            if (response != null) {
                return objectMapper.readValue(response, new TypeReference<Map<String, Object>>() {
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // fallback
        Map<String, Object> fallback = new HashMap<>();
        fallback.put("error", "可视化失败，请检查参数设置");
        return fallback;
    }

    // 保留旧方法以确保兼容性
    @Override
    public Map<String, Object> processBoreholeEllipticity(
            MultipartFile ttFile, 
            MultipartFile wttFile, 
            MultipartFile maskFile,
            Double rp, 
            Double vf, 
            Double wtt, 
            Double beta) {
        
        try {
            // 构建multipart请求
            var multipartData = BodyInserters.fromMultipartData("tt_file", ttFile.getResource())
                .with("rp", String.valueOf(rp))
                .with("vf", String.valueOf(vf));
            
            if (wttFile != null) {
                multipartData = multipartData.with("wtt_file", wttFile.getResource());
            }
            
            if (maskFile != null) {
                multipartData = multipartData.with("mask_file", maskFile.getResource());
            }
            
            if (wtt != null) {
                multipartData = multipartData.with("wtt", String.valueOf(wtt));
            }
            
            if (beta != null) {
                multipartData = multipartData.with("beta", String.valueOf(beta));
            }

            String response = webClient.post()
                    .uri(pythonServiceUrl + "/borehole/process")  // 保持原来的端点
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(multipartData)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();

            if (response != null) {
                return objectMapper.readValue(response, new TypeReference<Map<String, Object>>() {
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        
        // fallback
        Map<String, Object> fallback = new HashMap<>();
        fallback.put("error", "处理失败，请检查文件格式和参数设置");
        return fallback;
    }
} 