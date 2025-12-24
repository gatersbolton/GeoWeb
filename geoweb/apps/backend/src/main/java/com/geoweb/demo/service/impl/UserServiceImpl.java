package com.geoweb.demo.service.impl;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.geoweb.demo.entity.User;
import com.geoweb.demo.mapper.UserMapper;
import com.geoweb.demo.service.UserService;

@Service
public class UserServiceImpl implements UserService {
    @Autowired
    private UserMapper userMapper;

    @Override
    public boolean register(User user) {
        if (userMapper.findByUsername(user.getUsername()) != null) {
            return false; // 用户名已存在
        }
        userMapper.insertUser(user);
        return true;
    }

    @Override
    public java.util.List<User> listAll() {
        return userMapper.findAll();
    }

    @Override
    public User login(String username, String password) {
        User user = userMapper.findByUsername(username);
        if (user != null && user.getPassword().equals(password)) {
            return user;
        }
        return null;
    }

    @Override
    public User findByUsername(String username) {
        return userMapper.findByUsername(username);
    }

    @Override
    public User findById(Integer id) {
        return userMapper.findById(id);
    }

    @Override
    public boolean updateProfile(User user) {
        return userMapper.updateProfile(user) > 0;
    }

    @Override
    public boolean updatePassword(Integer id, String password) {
        return userMapper.updatePassword(id, password) > 0;
    }
}
