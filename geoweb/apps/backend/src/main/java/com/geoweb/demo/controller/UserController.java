package com.geoweb.demo.controller;

import java.util.HashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.geoweb.demo.entity.User;
import com.geoweb.demo.service.UserService;

@RestController
@RequestMapping("/user")
public class UserController {
    @Autowired
    private UserService userService;

    @PostMapping("/register")
    public String register(@RequestBody User user) {
        boolean success = userService.register(user);
        return success ? "注册成功" : "用户名已存在";
    }

    @PostMapping("/login")
    public String login(@RequestBody User user) {
        User loggedIn = userService.login(user.getUsername(), user.getPassword());
        return loggedIn != null ? "登录成功" : "用户名或密码错误";
    }

    @GetMapping("/list")
    public java.util.List<User> listUsers() {
        return userService.listAll();
    }

    @GetMapping("/profile")
    public User getProfile(@RequestParam("username") String username) {
        User user = userService.findByUsername(username);
        if (user != null) {
            user.setPassword(null);
        }
        return user;
    }

    @PutMapping("/profile")
    public Map<String, Object> updateProfile(@RequestBody User user) {
        Map<String, Object> result = new HashMap<>();
        if (user.getId() == null) {
            result.put("success", false);
            result.put("message", "缺少用户ID");
            return result;
        }
        User current = userService.findById(user.getId());
        if (current == null) {
            result.put("success", false);
            result.put("message", "用户不存在");
            return result;
        }
        if (user.getUsername() == null || user.getUsername().trim().isEmpty()) {
            result.put("success", false);
            result.put("message", "用户名不能为空");
            return result;
        }
        User existing = userService.findByUsername(user.getUsername());
        if (existing != null && !existing.getId().equals(user.getId())) {
            result.put("success", false);
            result.put("message", "用户名已存在");
            return result;
        }
        boolean updated = userService.updateProfile(user);
        result.put("success", updated);
        result.put("message", updated ? "个人资料更新成功" : "更新失败");
        return result;
    }

    @PutMapping("/password")
    public Map<String, Object> updatePassword(@RequestBody PasswordUpdateRequest request) {
        Map<String, Object> result = new HashMap<>();
        if (request.getId() == null) {
            result.put("success", false);
            result.put("message", "缺少用户ID");
            return result;
        }
        if (request.getCurrentPassword() == null || request.getCurrentPassword().trim().isEmpty()) {
            result.put("success", false);
            result.put("message", "当前密码不能为空");
            return result;
        }
        if (request.getNewPassword() == null || request.getNewPassword().trim().isEmpty()) {
            result.put("success", false);
            result.put("message", "新密码不能为空");
            return result;
        }
        User user = userService.findById(request.getId());
        if (user == null) {
            result.put("success", false);
            result.put("message", "用户不存在");
            return result;
        }
        if (!user.getPassword().equals(request.getCurrentPassword())) {
            result.put("success", false);
            result.put("message", "当前密码错误");
            return result;
        }
        boolean updated = userService.updatePassword(request.getId(), request.getNewPassword());
        result.put("success", updated);
        result.put("message", updated ? "密码更新成功" : "更新失败");
        return result;
    }

    public static class PasswordUpdateRequest {
        private Integer id;
        private String currentPassword;
        private String newPassword;

        public Integer getId() {
            return id;
        }

        public void setId(Integer id) {
            this.id = id;
        }

        public String getCurrentPassword() {
            return currentPassword;
        }

        public void setCurrentPassword(String currentPassword) {
            this.currentPassword = currentPassword;
        }

        public String getNewPassword() {
            return newPassword;
        }

        public void setNewPassword(String newPassword) {
            this.newPassword = newPassword;
        }
    }
} 
