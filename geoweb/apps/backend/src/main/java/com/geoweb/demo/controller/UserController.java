package com.geoweb.demo.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
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
} 