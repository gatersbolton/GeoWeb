package com.geoweb.demo.controller;

import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.geoweb.demo.service.CsvService;

@RestController
@RequestMapping("/api/csv")
public class CsvController {

    @Autowired
    private CsvService csvService;

    @PostMapping(value = "/sum", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> sumCsv(@RequestPart("file") MultipartFile file) {
        return csvService.sumCsv(file);
    }
} 