package com.geoweb.demo.service;

import com.geoweb.demo.entity.User;

public interface UserService {
    boolean register(User user);
    java.util.List<User> listAll();
    User login(String username, String password);
    User findByUsername(String username);
    User findById(Integer id);
    boolean updateProfile(User user);
    boolean updatePassword(Integer id, String password);
} 
