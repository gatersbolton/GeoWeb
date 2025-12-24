package com.geoweb.demo.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.geoweb.demo.entity.User;

@Mapper
public interface UserMapper {
    int insertUser(User user);
    User findByUsername(@Param("username") String username);
    User findById(@Param("id") Integer id);
    java.util.List<User> findAll();
    int updateProfile(User user);
    int updatePassword(@Param("id") Integer id, @Param("password") String password);
}
