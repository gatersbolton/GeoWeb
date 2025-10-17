package com.geoweb.demo.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.HashMap;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.geoweb.demo.service.CsvService;

@Service
public class CsvServiceImpl implements CsvService {

    @Value("${python.service.url}")
    private String pythonServiceUrl;

    private final WebClient webClient = WebClient.builder().build();

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public Map<String, Object> sumCsv(MultipartFile file) {
        try {
            String response = webClient.post()
                    .uri(pythonServiceUrl + "/process")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(BodyInserters.fromMultipartData("file", file.getResource()))
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
        fallback.put("sum", 0);
        fallback.put("plot", null);
        return fallback;
    }
} 