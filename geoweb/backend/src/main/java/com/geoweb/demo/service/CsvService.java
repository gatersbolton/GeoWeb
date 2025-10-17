package com.geoweb.demo.service;

import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

public interface CsvService {
    Map<String, Object> sumCsv(MultipartFile file);
} 