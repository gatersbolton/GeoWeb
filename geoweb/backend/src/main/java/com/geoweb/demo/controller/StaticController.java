package com.geoweb.demo.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class StaticController {
    
    @GetMapping("/")
    public String index() {
        return "redirect:/borehole";
    }
    
    @GetMapping("/borehole")
    public String borehole() {
        return "forward:/borehole_ellipticity.html";
    }
}