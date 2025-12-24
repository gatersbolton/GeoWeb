package com.geoweb.demo.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.geoweb.demo.entity.User;

@Mapper
public interface UserMapper {
    int insertUser(User user);
    User findByUsername(@Param("username") String username);
    java.util.List<User> findAll();
} 