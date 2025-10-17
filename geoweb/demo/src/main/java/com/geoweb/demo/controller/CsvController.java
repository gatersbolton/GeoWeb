package com.geoweb.demo.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.bind.annotation.RequestParam;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/csv")
public class CsvController {

    @PostMapping("/sum")
    public ResponseEntity<Map<String, Object>> sumCsv(@RequestParam("file") MultipartFile file) throws IOException {
        double sum = 0;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(",");
                for (String p : parts) {
                    try {
                        sum += Double.parseDouble(p.trim());
                    } catch (NumberFormatException ignored) {
                        // ignore non-numeric
                    }
                }
            }
        }
        Map<String, Object> result = new HashMap<>();
        result.put("sum", sum);
        return ResponseEntity.ok(result);
    }
} 