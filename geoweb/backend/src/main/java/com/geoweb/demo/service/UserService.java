package com.geoweb.demo.service;

import com.geoweb.demo.entity.User;

public interface UserService {
    boolean register(User user);
    java.util.List<User> listAll();
    User login(String username, String password);
} 