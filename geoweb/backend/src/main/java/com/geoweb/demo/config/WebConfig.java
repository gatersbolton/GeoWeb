package com.geoweb.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 添加前端静态资源映射
        registry.addResourceHandler("/**")
                .addResourceLocations("classpath:/static/", 
                                    "file:frontend/",
                                    "file:../frontend/");
    }
}